#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Matthew Davidson
# Created Date: 2024-02-02
# Copyright © 2024 Davidson Engineering Ltd.
# ---------------------------------------------------------------------------
"""network_simple - A simple network client and server for sending and receiving data."""
# ---------------------------------------------------------------------------


import time
import threading
import logging
import random
import time


logging.basicConfig(level=logging.INFO)

from network_simple.client import SimpleClientTCP
from network_simple.server import SimpleServerTCP

# Example server-client for networking with TCP protocol


def client_tcp():

    client_config = {
        "host": "localhost",
        "port": 9000,
    }
    client = SimpleClientTCP(**client_config)
    random_metrics = [
        dict(
            measurement="cpu_usage",
            fields=dict(cpu0=random.random()),
            time=time.time(),
        )
        for _ in range(16_384)
    ]
    for metric in random_metrics:
        client.add_to_queue(metric)
    client.run_until_buffer_empty()
    while True:
        time.sleep(1)


def server_tcp():
    buffer = []
    server = SimpleServerTCP(
        output_buffer=buffer,
        host="localhost",
        port=9000,
        autostart=True,
    )
    print(server)
    while True:
        time.sleep(1)


# Example server-client for networking with UDP protocol

from network_simple.client import SimpleClientUDP
from network_simple.server import SimpleServerUDP


def client_udp():

    client_config = {
        "host": "localhost",
        "port": 9001,
    }
    client = SimpleClientUDP(**client_config)
    random_metrics = [
        dict(
            measurement="cpu_usage",
            fields=dict(cpu0=random.random()),
            time=time.time(),
        )
        for _ in range(16_384)
    ]
    for metric in random_metrics:
        client.add_to_queue(metric)
    client.send()
    while True:
        time.sleep(1)


def server_udp():
    buffer = []
    server = SimpleServerUDP(
        output_buffer=buffer,
        host="localhost",
        port=9000,
        autostart=True,
    )
    print(server)
    while True:
        time.sleep(1)


# Run server and client in separate threads


def run_server(server):
    server_thread = threading.Thread(target=server)
    server_thread.start()
    return server_thread


def run_client(client):
    client_thread = threading.Thread(target=client)
    client_thread.start()
    return client_thread


def run_server_client(server, client):

    server_thread = run_server(server)
    time.sleep(0.5)
    client_thread = run_client(client)

    server_thread.join()
    client_thread.join()

    while True:
        time.sleep(1)


if __name__ == "__main__":

    # UDP client and server
    # run_server_client(server_udp, client_udp)

    run_client(client_tcp)
    while True:
        time.sleep(1)

    # TCP client and server
    # run_server_client(server_tcp, client_tcp)
