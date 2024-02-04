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
BUFFER_LENGTH = 16_384


def convert_bytes_to_human_readable(num: float) -> str:
    """Convert bytes to a human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} {unit}"


class SimpleClient(ABC):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 0,
        autostart: bool = False,
        update_interval: float = 1,
    ) -> None:
        self.host = host
        self.port = port
        self.encoding = "utf-8"
        self._buffer = PackagedBuffer(maxlen=BUFFER_LENGTH, packager=JSONPackager())
        self.update_interval = update_interval
        self.run_client_thread = threading.Thread(target=self.run_client, daemon=True)
        if autostart:
            self.start()

    @abstractmethod
    def send(self) -> None: ...

    def finish(self) -> None:
        pass

    def add_to_queue(self, data: Any) -> None:
        self._buffer.add(data)

    def run_client(self) -> None:
        while True:
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
        while self._buffer.not_empty():
            self.send()
            self.finish()
            logger.info("Waiting for buffer to empty")
            time.sleep(self.update_interval)
        else:
            logger.info("Buffer empty")

    def finish(self) -> None:
        bytes_recvd_str = convert_bytes_to_human_readable(self.bytes_sent)
        logger.info(f"Sent {bytes_recvd_str} to {self.host}")

    def __enter__(self) -> SimpleClient:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def __del__(self):
        self.stop()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.host}, {self.port})"


class SimpleClientTCP(SimpleClient):
    def send(self) -> None:
        self.bytes_sent = 0
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            try:
                with io.TextIOWrapper(
                    s.makefile("rwb"), encoding=self.encoding, newline="\n"
                ) as stream:
                    while self._buffer.not_empty():
                        packet = self._buffer.next_packed(terminator="\n")
                        self.bytes_sent += len(packet.strip())
                        logger.debug(f"Sending packet to {self.host}: {packet.strip()}")
                        stream.write(packet)
                        stream.flush()
            except Exception as e:
                logger.error(f"Error in client send: {e}")


class SimpleClientUDP(SimpleClient):
    def send(self) -> None:
        self.bytes_sent = 0
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            while self._buffer.not_empty():
                packet = self._buffer.next_packed(terminator="\n")
                self.bytes_sent += len(packet.strip())
                logger.debug(f"Sending packet to {self.host}: {packet.strip()}")
                s.sendto(packet.encode(self.encoding), (self.host, self.port))


def TCP_client():
    import logging
    import random

    logging.basicConfig(level=logging.DEBUG)
    client_config = {
        "host": "localhost",
        "port": 9000,
    }

    client = SimpleClientTCP(**client_config)
    random_metrics = [("cpu_usage", random.random(), time.time()) for _ in range(4095)]

    # Example: Add metrics to the buffer
    for metric in random_metrics:
        client.add_to_queue(metric)
    # Example: Send the buffer to the server
    client.send()
    while True:
        time.sleep(1)


def UDP_client():
    import logging
    import random

    logging.basicConfig(level=logging.DEBUG)
    client_config = {
        "host": "localhost",
        "port": 9000,
    }

    client = SimpleClientUDP(**client_config)
    random_metrics = [("cpu_usage", random.random(), time.time()) for _ in range(4095)]

    # Example: Add metrics to the buffer
    for metric in random_metrics:
        client.add_to_queue(metric)
    # Example: Send the buffer to the server
    client.send()
    while True:
        time.sleep(1)


if __name__ == "__main__":
    # UDP_client()
    TCP_client()
