### Broker application for RIOT demo

The broker manage a list of alive sensor nodes by listening on an UDP port.
The list of alive nodes can be retrieved using HTTP from any host on a
network.

By default, the UDP port is listening on port 8888 and HTTP url is
`http://<your_broker_host>:8000/nodes`

The alive nodes are retrieved in the following json format:
{ 'node':
 [ ip1, ip2, ip3]
}

If a sensor node has not sent a update within 60s, it's removed from the
list of alived nodes automatically.
