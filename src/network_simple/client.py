#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Matthew Davidson
# Created Date: 2024-02-02
# Copyright © 2024 Davidson Engineering Ltd.
# ---------------------------------------------------------------------------

from __future__ import annotations
import socket
from datetime import datetime, timezone
from typing import Union
import socket
import time
import threading
import logging
from abc import ABC, abstractmethod

from buffered.buffer import PackagedBuffer, JSONPackager

logger = logging.getLogger(__name__)


MAXIMUM_PACKET_SIZE = 4096


class SimpleClient(ABC):
    def __init__(self, host="localhost", port=0, autostart=False, update_interval=1):
        self.host = host
        self.port = port
        self._buffer = PackagedBuffer(packager=JSONPackager())
        self.update_interval = update_interval
        self.run_client_thread = threading.Thread(target=self.run_client, daemon=True)
        if autostart:
            self.start()

    @abstractmethod
    def send(self): ...

    def add_to_queue(self, data):
        self._buffer.add(data)

    def run_client(self):
        while True:
            self.send()
            time.sleep(self.update_interval)

    def start(self):
        self.run_client_thread.start()
        logger.debug("Started client thread")
        return self

    def stop(self):
        self.run_client_thread.join()
        logger.debug("Stopped client thread")

    def run_until_buffer_empty(self):
        while self._buffer.not_empty():
            self.send()
            logger.info("Waiting for buffer to empty")
            time.sleep(self.update_interval)
        else:
            logger.info("Buffer empty")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def __del__(self):
        self.stop()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.host}, {self.port})"


class SimpleClientTCP(SimpleClient):
    def send(self):
        while self._buffer.not_empty():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                packet = self._buffer.pack_next()
                logger.debug(f"Sending packet: {packet}")
                s.send(packet)


class SimpleClientUDP(SimpleClient):
    def send(self):
        while self._buffer.not_empty():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                packet = self._buffer.pack_next()
                logger.debug(f"Sending packet: {packet}")
                s.sendto(packet, (self.host, self.port))


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
