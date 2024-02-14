#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Matthew Davidson
# Created Date: 2024-02-02
# Copyright © 2024 Davidson Engineering Ltd.
# ---------------------------------------------------------------------------

from __future__ import annotations
import socket
from typing import Any
import socket
import time
import threading
import logging
from abc import ABC, abstractmethod
import io

from buffered.buffer import PackagedBuffer, JSONPackager

logger = logging.getLogger(__name__)


MAXIMUM_PACKET_SIZE = 4_096
BUFFER_LENGTH = 65_536


def convert_bytes_to_human_readable(num: float) -> str:
    """Convert bytes to a human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} {unit}"


def shorten_data(data: str, max_length: int = 75) -> str:
    """Shorten data to a maximum length."""
    if not isinstance(data, str):
        data = str(data)
    data = data.strip()
    return data[:max_length] + "..." if len(data) > max_length else data


class SimpleClient(ABC):
    def __init__(
        self,
        server_address: tuple[str, int] = ("localhost", 0),
        autostart: bool = True,
        update_interval: float = 1,
    ) -> None:
        self.server_address = server_address
        self.host = server_address[0]
        self.encoding = "utf-8"
        self._output_buffer = PackagedBuffer(
            maxlen=BUFFER_LENGTH, packager=JSONPackager(terminator="\n")
        )
        self._input_buffer = PackagedBuffer(
            maxlen=BUFFER_LENGTH, packager=JSONPackager(terminator="\n")
        )
        self.update_interval = update_interval
        self.run_client_thread = threading.Thread(target=self.run_client, daemon=True)
        if autostart:
            self.start()

    @abstractmethod
    def send(self) -> None: ...

    @abstractmethod
    def receive(self) -> None: ...

    def finish(self) -> None:
        pass

    def add_to_queue(self, data: Any) -> None:
        if isinstance(data, (list, tuple)):
            for el in data:
                self._output_buffer.put(el)
        else:
            self._output_buffer.put(data)

    def run_client(self) -> None:
        while True:
            if self._output_buffer.not_empty():
                self.send()
            time.sleep(self.update_interval)

    def start(self) -> SimpleClient:
        self.run_client_thread.start()
        logger.debug("Started client thread")
        return self

    def stop(self) -> None:
        self.run_client_thread.join()
        logger.debug("Stopped client thread")

    def run_until_buffer_empty(self) -> None:
        while self._output_buffer.not_empty():
            self.send()
            self.finish()
            logger.info("Waiting for buffer to empty")
            # Courtesy wait
            time.sleep(self.update_interval)
        else:
            logger.info("Buffer empty")

    def finish(self) -> None:
        bytes_recvd_str = convert_bytes_to_human_readable(self.bytes_sent)
        logger.info(f"Sent {bytes_recvd_str} to {str(self)}")

    def __enter__(self) -> SimpleClient:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def __del__(self):
        self.stop()

    @property
    def server_address_str(self) -> str:
        return f"{self.server_address[0]}:{self.server_address[1]}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.server_address_str})"


class SimpleClientTCP(SimpleClient):
    def send(self) -> None:
        self.bytes_sent = 0
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(self.server_address)
            try:
                with io.TextIOWrapper(
                    s.makefile("rwb"), encoding=self.encoding, newline="\n"
                ) as stream:
                    while self._output_buffer.not_empty():
                        data = self._output_buffer.next_packed()
                        self.bytes_sent += len(data.strip())
                        logger.debug(
                            f"Sent to server@{self.server_address_str}: {shorten_data(data)}"
                        )
                        stream.write(data)
                        stream.flush()
            except Exception as e:
                logger.error(f"Error in client send: {e}")

    def receive(self):
        self.bytes_received = 0
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(self.client_address)
            s.listen()
            logger.debug(f"Waiting for connection on {self}")
            connection, client_address = s.accept()
            with io.TextIOWrapper(
                connection.makefile("rwb"), encoding=self.encoding, newline="\n"
            ) as stream:
                try:
                    while True:
                        data = stream.readline()
                        self._input_buffer.put(data)
                        if not data:
                            break  # No more data, connection closed
                        self.bytes_received += len(data.strip())
                        logger.debug(
                            f"Received from server@{self.server_address_str}: {shorten_data(data)}"
                        )
                        # Process the received data as needed
                except Exception as e:
                    logger.error(f"Error in client receive: {e}")


class SimpleClientUDP(SimpleClient):
    def send(self) -> None:
        self.bytes_sent = 0
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            while self._input_buffer.not_empty():
                data = self._input_buffer.next_packed()
                self.bytes_sent += len(data.strip())
                logger.debug(f"Sent to {self.server_address_str}: {shorten_data(data)}")
                s.sendto(data.encode(self.encoding), self.server_address)

    def receive(self):
        self.bytes_recvd = 0
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            while data := self.rfile.readline(MAXIMUM_PACKET_SIZE).decode().strip():
                self.server._input_buffer.append(data)
                self.bytes_recvd += len(data)
            packet = self._buffer.next_packed()
            self.bytes_sent += len(packet.strip())
            logger.debug(f"Received from {self.host}: {shorten_data(data)}")
            s.sendto(packet.encode(self.encoding), (self.host, self.port))


def test_tcp_client():
    import logging
    import random

    logging.basicConfig(level=logging.INFO)
    server_address = ("localhost", 9000)

    client = SimpleClientTCP(server_address)

    random_metrics = [
        {
            "measurement": "cpu_usage",
            "fields": {"cpu0": random.random(), "cpu1": 1 - random.random()},
            "tags": {"host": "localhost", "region": "us-west"},
            "time": time.time(),
        }
        for _ in range(5000)
    ]

    # Example: Add metrics to the buffer
    client.add_to_queue(random_metrics)
    # Example: Send the buffer to the server
    client.send()
    client.run_until_buffer_empty()


def test_udp_client():
    import logging
    import random

    logging.basicConfig(level=logging.INFO)
    server_address = ("localhost", 9000)

    client = SimpleClientUDP(server_address)
    random_metrics = [("cpu_usage", random.random(), time.time()) for _ in range(4095)]

    # Example: Add metrics to the buffer
    client.add_to_queue(random_metrics)
    # Example: Send the buffer to the server
    client.send()
    client.run_until_buffer_empty()


if __name__ == "__main__":
    # test_udp_client()
    test_tcp_client()
