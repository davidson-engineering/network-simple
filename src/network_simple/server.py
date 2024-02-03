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
import bufsock

from buffered.buffer import Buffer, PackagedBuffer, JSONPackager, Packager

logger = logging.getLogger(__name__)
server_logbook = logging.getLogger("server_conn")

MAXIMUM_PACKET_SIZE = 4096
BUFFER_LENGTH = 8192


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


class SimpleHandler:
    def handle(self) -> None:
        try:
            data = self.rfile.readline(MAXIMUM_PACKET_SIZE)
            self.server._input_buffer.append(data)
            length = len(data)
            # ignore any blank data
            if is_empty(data):
                return
            logger.info(
                f"Received {length} bytes of data from {self.client_address[0]}"
            )
        except Exception as e:
            logger.error(e)


class SimpleHandlerUDP(SimpleHandler, socketserver.DatagramRequestHandler): ...


class SimpleHandlerTCP(SimpleHandler, socketserver.StreamRequestHandler): ...


class SimpleServer:

    _timeout = 5  # seconds (not implemented yet)
    _start_time = time.monotonic()

    def __init__(
        self,
        output_buffer: Union[List, deque],
        buffer_length: int = BUFFER_LENGTH,
        autostart: bool = False,
        host: str = "localhost",
        port: int = 0,
        update_interval: float = 0.5,
        packager: Packager = None,
    ) -> None:

        self.host = host
        self.port = port
        self.update_interval = update_interval

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
        return self._input_buffer.unpack()

    def peek_buffer(self) -> List[bytes]:
        return self._input_buffer.get_copy()

    def handle_connections(self) -> None:
        logger.info(
            f"Starting server on {self.server_address[0]} at port {self.server_address[1]}"
        )
        self.serve_forever(poll_interval=self.update_interval)

    def unpack_input_buffer(self) -> None:
        while True:
            while len(self._input_buffer) > 0:
                try:
                    decoded_data = self._input_buffer.unpack_next()
                    self._output_buffer.append(decoded_data)
                except AttributeError:
                    self._output_buffer.append(self._input_buffer.pop())
            time.sleep(self.update_interval)

    def start(self) -> None:
        self.handler_thread.start()
        self.unpacking_thread.start()

    def stop(self) -> None:
        logger.info(
            f"Stopping server on {self.server_address[0]} at port {self.server_address[1]}"
        )
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
        return f"{self.__class__.__name__}({self.host}, {self.port})"

    def __str__(self):
        return f"{self.__class__.__name__}({self.host}, {self.port})"


class SimpleServerTCP(SimpleServer, socketserver.TCPServer):
    def __init__(
        self,
        output_buffer: Union[List, deque] = None,
        host: str = "localhost",
        port: int = 0,
        RequestHandlerClass: StreamRequestHandler = SimpleHandlerTCP,
        autostart: bool = True,
        buffer_length: int = BUFFER_LENGTH,
        **kwargs,
    ) -> None:
        socketserver.TCPServer.__init__(
            self, (host, port), RequestHandlerClass, **kwargs
        )
        SimpleServer.__init__(
            self,
            output_buffer=output_buffer,
            buffer_length=buffer_length,
            autostart=autostart,
            host=host,
            port=port,
            **kwargs,
        )

    def get_request(self) -> tuple[socket.socket, str]:
        conn, addr = super().get_request()
        logger.info("Connection from %s:%s", *addr)
        server_logbook.info(
            f"Server at {self.server_address[0]}:{self.server_address[1]} connected to {addr[0]}:{addr[1]}"
        )
        self._socket_buffer = bufsock.bufsock(conn)
        return conn, addr


class SimpleServerUDP(SimpleServer, socketserver.UDPServer):
    def __init__(
        self,
        output_buffer: Union[List, deque] = None,
        host: str = "localhost",
        port: int = 0,
        RequestHandlerClass: DatagramRequestHandler = SimpleHandlerUDP,
        autostart: bool = True,
        buffer_length: int = BUFFER_LENGTH,
        **kwargs,
    ) -> None:
        socketserver.UDPServer.__init__(
            self, (host, port), RequestHandlerClass, **kwargs
        )
        SimpleServer.__init__(
            self,
            output_buffer=output_buffer,
            buffer_length=buffer_length,
            autostart=autostart,
            host=host,
            port=port,
            **kwargs,
        )

    def get_request(self) -> tuple[socket.socket, str]:
        (data, self.socket), addr = super().get_request()
        logger.info("Connection from %s:%s", *addr)
        server_logbook.info(
            f"Server at {self.server_address[0]}:{self.server_address[1]} connected to {addr[0]}:{addr[1]}"
        )
        return (data, self.socket), addr


def simple_tcp_server() -> None:
    buffer = []
    server = SimpleServerTCP(
        output_buffer=buffer,
        host="localhost",
        port=9000,
        autostart=True,
    )
    print(server)

    while True:
        print(len(buffer))
        time.sleep(1)


def simple_udp_server() -> None:
    buffer = Buffer()
    server = SimpleServerUDP(
        output_buffer=buffer,
        host="localhost",
        port=9000,
        autostart=True,
    )
    print(server)

    while True:
        print(len(buffer))
        time.sleep(1)


if __name__ == "__main__":
    simple_tcp_server()
    # simple_udp_server()
