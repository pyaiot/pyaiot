"""Broker application used to register sensor nodes."""

from errno import EWOULDBLOCK, EAGAIN
import logging
import os
import socket
import time

from tornado import web
from tornado.ioloop import IOLoop
from tornado.netutil import set_close_exec

_RETENTION_TIME = 120  # seconds
_UDP_PORT = 8888
_HTTP_PORT = 8000
_NODE_LIST = {}

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - '
                           '%(levelname)s - %(message)s')


def _cleanup_node_list():
    global _NODE_LIST
    result_dict = {'nodes': []}
    current_time = int(time.time())
    for ip, dt in _NODE_LIST.items():
        if current_time < dt + _RETENTION_TIME:
            result_dict['nodes'].append(ip)

    return result_dict


class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        nodes = _cleanup_node_list()
        self.write(nodes)
        self.finish()

    @web.asynchronous
    def post(self):
        pass


class UDPServer(object):
    """UDP server class."""

    def __init__(self, name, port, on_receive, address=None,
                 family=socket.AF_INET6, io_loop=None):
        """Constructor."""
        self.io_loop = io_loop or IOLoop.instance()
        self._on_receive = on_receive
        self._log = logging.getLogger(name)
        self._sockets = []

        flags = socket.AI_PASSIVE

        if hasattr(socket, "AI_ADDRCONFIG"):
            flags |= socket.AI_ADDRCONFIG

        # find all addresses to bind, bind and register the "READ" callback
        for res in set(socket.getaddrinfo(address, port,
                                          family,
                                          socket.SOCK_DGRAM, 0, flags)):
            af, sock_type, proto, canon_name, sock_addr = res
            self._open_and_register(af, sock_type, proto, sock_addr)

        self._log.debug('Started')

    def _open_and_register(self, af, sock_type, proto, sock_addr):
        sock = socket.socket(af, sock_type, proto)
        set_close_exec(sock.fileno())
        if os.name != 'nt':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)

        self._log.debug('Binding to %s...', repr(sock_addr))
        sock.bind(sock_addr)

        def read_handler(fd, events):
            while True:
                try:
                    data, address = sock.recvfrom(65536)
                except socket.error as e:
                    if e.args[0] in (EWOULDBLOCK, EAGAIN):
                        return
                    raise
                self._on_receive(data, address)

        self.io_loop.add_handler(sock.fileno(), read_handler, IOLoop.READ)
        self._sockets.append(sock)

    def stop(self):
        """Stop the UDP server."""
        self._log.debug('Closing %d socket(s)...', len(self._sockets))
        for sock in self._sockets:
            self.io_loop.remove_handler(sock.fileno())
            sock.close()


def custom_on_receive(data, address):
    """Callback triggered when a message is received."""
    _NODE_LIST.update({address[0]: int(time.time())})
    logging.info('CUSTOM: %s - %s', address, data)


def main():
    """Main function of the UDP server."""
    server = UDPServer('UDPServer', _UDP_PORT, on_receive=custom_on_receive)
    app = web.Application([
        (r'/nodes', ApiHandler),
    ])

    app.listen(_HTTP_PORT)
    IOLoop.instance().start()


if __name__ == '__main__':
    main()
