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


logging.basicConfig(level=logging.INFO)

# Example server-client for networking with TCP protocol


def client_tcp():

    import random
    import time

    from network_simple import SimpleClientTCP

    client = SimpleClientTCP(
        server_address=("gfyvrdatadash", 50000),
    )
    random_metrics = [
        dict(
            measurement="cpu_usage",
            fields=dict(cpu0=random.random()),
            time=time.time(),
        )
        for _ in range(65_384)
    ]
    client.add_to_queue(random_metrics)
    client.run_until_buffer_empty()

    while True:
        time.sleep(1)


def server_tcp():

    import time

    from network_simple import SimpleServerTCP
    from buffered.buffer import Buffer

    buffer = Buffer()

    server = SimpleServerTCP(
        output_buffer=buffer,
        server_address=("localhost", 50000),
        autostart=True,
    )
    # Wait here, server will run in the background
    while True:
        time.sleep(1)


# Example server-client for networking with UDP protocol
def client_udp():

    import random
    import time

    from network_simple import SimpleClientUDP

    client = SimpleClientUDP(
        server_address=("localhost", 9000),
    )
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

    import time

    from network_simple import SimpleServerUDP
    from buffered.buffer import Buffer

    buffer = Buffer()
    server = SimpleServerUDP(
        output_buffer=buffer,
        server_address=("localhost", 9000),
        autostart=True,
    )
    # Wait here, server will run in the background
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
    # run_server_client(server_tcp, client_tcp)
    client_tcp()
    # run_client(client_tcp)

    while True:
        time.sleep(1)

    # TCP client and server
    # run_server_client(server_tcp, client_tcp)
