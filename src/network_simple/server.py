#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Matthew Davidson
# Created Date: 2024-02-02
# Copyright © 2024 Davidson Engineering Ltd.
# ---------------------------------------------------------------------------

from __future__ import annotations
import socketserver
import socket
import logging
from socketserver import StreamRequestHandler, DatagramRequestHandler
from typing import Union, List
from collections import deque
import threading
import time
import io
from dataclasses import dataclass

from buffered.buffer import Buffer, PackagedBuffer, JSONPackager, Packager
from application_metrics import ApplicationMetrics, SessionMetrics

logger = logging.getLogger(__name__)
server_logbook = logging.getLogger("server_conn")

MAXIMUM_PACKET_SIZE = 4_096
BUFFER_LENGTH = 16_384


DEFAULT_SERVER_ADDRESS_TCP = ("localhost", 0)
DEFAULT_SERVER_ADDRESS_UDP = ("localhost", 0)


@dataclass
class ServerStatistics(ApplicationMetrics):
    connections_received: int = 0
    connections_sent: int = 0
    connections_failed: int = 0
    connections_buffered: int = 0
    connections_dropped: int = 0
    connections_processed: int = 0
    bytes_received: float = 0
    bytes_sent: float = 0


def is_empty(obj) -> bool:
    if isinstance(obj, str):
        return not bool(obj.strip())  # Consider empty strings as true
    elif isinstance(obj, list):
        return all(
            is_empty(element) for element in obj
        )  # Recursively check elements in lists
    else:
        return not bool(obj)  # Other non-list, non-string objects are considered true


def string_to_binary(string) -> bytes:
    """Convert a text string (or binary string type) to a binary string type."""
    if isinstance(string, str):
        return string.encode("utf-8")
    return string


def convert_bytes_to_human_readable(num: float) -> str:
    """Convert bytes to a human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} {unit}"


class SimpleHandler:
    def finish(self) -> None:
        self.server.session_stats.increment("bytes_received", self.bytes_recvd)
        bytes_recvd_str = convert_bytes_to_human_readable(self.bytes_recvd)
        logger.info(
            f"Received {bytes_recvd_str} from {self.client_address[0]}:{self.client_address[1]}"
        )


class SimpleHandlerUDP(SimpleHandler, socketserver.DatagramRequestHandler):
    def handle(self) -> None:
        self.bytes_recvd = 0
        try:
            while data := self.rfile.readline(MAXIMUM_PACKET_SIZE).decode().strip():
                self.server._input_buffer.append(data)
                self.bytes_recvd += len(data)
        except Exception as e:
            logger.error(e)


class SimpleHandlerTCP(SimpleHandler, socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.bytes_recvd = 0
        try:
            with io.TextIOWrapper(
                self.connection.makefile("rwb"), encoding="utf-8", newline="\n"
            ) as stream:
                while data := stream.readline(MAXIMUM_PACKET_SIZE).strip():
                    self.server._input_buffer.append(data)
                    self.bytes_recvd += len(data)
        except Exception as e:
            logger.error(e)


class SimpleServer:

    _timeout = 5  # seconds (not implemented yet)
    _start_time = time.monotonic()

    def __init__(
        self,
        output_buffer: Union[List, deque],
        buffer_length: int = BUFFER_LENGTH,
        autostart: bool = False,
        server_address=("localhost", 0),
        update_interval: float = 0.5,
        packager: Packager = None,
    ) -> None:

        self.server_address = server_address
        self.update_interval = update_interval

        self.session_stats = SessionMetrics(
            total_stats=ServerStatistics(),
            period_stats=ServerStatistics(),
        )

        self._output_buffer = output_buffer
        self._input_buffer = PackagedBuffer(
            maxlen=buffer_length, packager=packager or JSONPackager()
        )

        handler_thread: threading.Thread = threading.Thread(
            target=self.handle_connections, daemon=True
        )

        unpacking_thread: threading.Thread = threading.Thread(
            target=self.unpack_input_buffer, daemon=True
        )

        if autostart:
            handler_thread.start()
            unpacking_thread.start()

        self.handler_thread = handler_thread
        self.unpacking_thread = unpacking_thread

    def fetch_buffer(self) -> List[bytes]:
        return self._input_buffer._unpack()

    def peek_buffer(self) -> List[bytes]:
        return self._input_buffer.get_copy()

    def handle_connections(self) -> None:
        logger.info(f"Starting server {str(self)}")
        self.serve_forever(poll_interval=self.update_interval)

    def unpack_input_buffer(self) -> None:
        while True:
            while len(self._input_buffer) > 0:
                try:
                    data = self._input_buffer.next_unpacked()
                    self._output_buffer.append(data)
                except AttributeError:
                    self._output_buffer.append(next(self._input_buffer))
            time.sleep(self.update_interval)

    def start(self) -> None:
        self.handler_thread.start()
        self.unpacking_thread.start()

    def stop(self) -> None:
        logger.info(f"Stopping server {str(self)}")
        logger.info(f"Uptime: {time.monotonic() - SimpleServer._start_time} seconds")
        self.shutdown()
        self.handler_thread.join()
        self.unpacking_thread.join()

    def __del__(self):
        self.stop()
        logger.info("Server thread stopped")
        super().__del__()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        logger.info("Server thread stopped")
        super().__exit__(exc_type, exc_value, traceback)

    def __enter__(self):
        return self

    def __repr__(self):
        return f"{self.__class__.__name__}({self.server_address[0]}:{self.server_address[1]})"

    def __str__(self):
        return f"{self.__class__.__name__}({self.server_address[0]}:{self.server_address[1]})"


class SimpleServerTCP(SimpleServer, socketserver.TCPServer):
    def __init__(
        self,
        output_buffer: Union[List, deque] = None,
        server_address=DEFAULT_SERVER_ADDRESS_TCP,
        RequestHandlerClass: StreamRequestHandler = SimpleHandlerTCP,
        autostart: bool = True,
        buffer_length: int = BUFFER_LENGTH,
        **kwargs,
    ) -> None:
        socketserver.TCPServer.__init__(
            self, server_address, RequestHandlerClass, **kwargs
        )
        SimpleServer.__init__(
            self,
            output_buffer=output_buffer,
            buffer_length=buffer_length,
            autostart=autostart,
            server_address=server_address,
            **kwargs,
        )

    def get_request(self) -> tuple[socket.socket, str]:
        conn, addr = super().get_request()
        logger.info("Connection from %s:%s", *addr)
        server_logbook.info(f"Server {self} connected to {addr[0]}:{addr[1]}")
        self.session_stats.increment("connections_received")
        # self._socket_buffer = bufsock.bufsock(conn)
        return conn, addr


class SimpleServerUDP(SimpleServer, socketserver.UDPServer):
    def __init__(
        self,
        output_buffer: Union[List, deque] = None,
        server_address=DEFAULT_SERVER_ADDRESS_UDP,
        RequestHandlerClass: DatagramRequestHandler = SimpleHandlerUDP,
        autostart: bool = True,
        buffer_length: int = BUFFER_LENGTH,
        **kwargs,
    ) -> None:
        socketserver.UDPServer.__init__(
            self, server_address, RequestHandlerClass, **kwargs
        )
        SimpleServer.__init__(
            self,
            output_buffer=output_buffer,
            buffer_length=buffer_length,
            autostart=autostart,
            server_address=server_address,
            **kwargs,
        )

    def get_request(self) -> tuple[socket.socket, str]:
        (data, self.socket), addr = super().get_request()
        logger.info("Connection from %s:%s", *addr)
        server_logbook.info(f"{self} connected to {addr[0]}:{addr[1]}")
        self.session_stats.increment("connections_received")
        return (data, self.socket), addr


def simple_tcp_server() -> None:
    buffer = []
    server = SimpleServerTCP(
        output_buffer=buffer,
        server_address=("localhost", 9000),
        autostart=True,
    )

    while True:
        print(len(buffer))
        time.sleep(1)


def simple_udp_server() -> None:
    buffer = Buffer()
    server = SimpleServerUDP(
        output_buffer=buffer,
        server_address=("localhost", 9000),
        autostart=True,
    )

    while True:
        print(len(buffer))
        time.sleep(1)


if __name__ == "__main__":
    # simple_tcp_server()
    # simple_udp_server()
    pass
