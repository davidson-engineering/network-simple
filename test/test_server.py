#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Matthew Davidson
# Created Date: 2024-02-02
# Copyright © 2024 Davidson Engineering Ltd.
# ---------------------------------------------------------------------------

from __future__ import annotations
from typing import Any

import pytest

import time
import logging


logger = logging.getLogger(__name__)


def calc_mean(metrics: list[dict[str, Any]], field) -> float:
    """Calculate the average value of a list of metrics."""
    return sum([metric["fields"][field] for metric in metrics]) / len(metrics)


def calc_var(metrics: list[dict[str, Any]], field) -> float:
    """Calculate the variance of a list of metrics."""
    average_value = calc_mean(metrics, field)
    return sum(
        [(metric["fields"][field] - average_value) ** 2 for metric in metrics]
    ) / len(metrics)


def send_random_metrics(size: int, client, server):
    import random

    random_metrics = [
        dict(
            measurement="cpu_usage",
            fields=dict(cpu0=random.random()),
            time=time.time(),
        )
        for _ in range(size)
    ]

    mean_source = calc_mean(random_metrics, "cpu0")
    var_source = calc_var(random_metrics, "cpu0")

    client.add_to_queue(random_metrics)
    client.run_until_buffer_empty()
    # Coutesy wait for the server to process the data
    time.sleep(3)
    server_metrics = server.dump_when_unpacked()

    mean_destination = calc_mean(server_metrics, "cpu0")
    var_destination = calc_var(server_metrics, "cpu0")

    assert len(server_metrics) == size
    assert mean_source == pytest.approx(mean_destination)
    assert var_source == pytest.approx(var_destination)


def test_client_small(server_tcp, client_tcp):

    server_address = ("localhost", 50001)
    server = server_tcp(server_address)
    client = client_tcp(server_address)

    # Small test to check that the client can send data to the server
    send_random_metrics(1024, client, server)


def test_client_large(server_tcp, client_tcp):

    server_address = ("localhost", 50002)
    server = server_tcp(server_address)
    client = client_tcp(server_address)

    # Increase number of metrics to test the buffer size
    send_random_metrics(16_384, client, server)


def test_client_huge(server_tcp, client_tcp):

    server_address = ("localhost", 50003)
    server = server_tcp(server_address)
    client = client_tcp(server_address)

    # Increase number of metrics to test the buffer size
    send_random_metrics(65_536, client, server)
