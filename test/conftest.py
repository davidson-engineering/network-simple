import pytest


@pytest.fixture
def server_tcp():

    def _server_tcp(server_address):

        from network_simple import SimpleServerTCP
        from buffered.buffer import Buffer

        buffer = Buffer(maxlen=65_536)
        server = SimpleServerTCP(
            output_buffer=buffer,
            server_address=server_address,
        )
        return server

    return _server_tcp


@pytest.fixture
def client_tcp():

    def _client_tcp(server_address):
        from network_simple import SimpleClientTCP

        client = SimpleClientTCP(
            server_address=server_address,
        )

        return client

    return _client_tcp


@pytest.fixture
def client_udp():

    def _client_udp(server_address):
        from network_simple import SimpleClientUDP

        client = SimpleClientUDP(
            server_address=server_address,
        )

        return client

    return _client_udp


@pytest.fixture
def server_udp():

    def _server_udp(server_address):
        from network_simple import SimpleServerUDP
        from buffered.buffer import Buffer

        buffer = Buffer(maxlen=65_536)
        server = SimpleServerUDP(
            output_buffer=buffer,
            server_address=server_address,
        )
        return server

    return _server_udp
