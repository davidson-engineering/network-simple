# network-simple
### A simple way to network apps, agents and processes

A simple python network client and server for sending and receiving data.


# Example server-client for networking with TCP protocol
```python
def client_tcp():

    import random
    import time

    from network_simple import SimpleClientTCP

    client = SimpleClientTCP(
        server_address=("localhost", 50000),
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
```
# Networking with UDP server and client
The implmentation is identical to the above, except using SimpleServerUDP and SimpleClientUDP classes.
