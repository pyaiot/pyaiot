"""Broker application used to register sensor nodes."""

from errno import EWOULDBLOCK, EAGAIN
import logging
import os
import sys
import socket
import time

from tornado import web
from tornado.ioloop import IOLoop
from tornado.netutil import set_close_exec
from tornado.options import define, options

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')


class NodesProvider(web.RequestHandler):

    _nodes = {}

    @web.asynchronous
    def get(self, *args):
        nodes = self._get_active_nodes()
        self.write(nodes)
        self.finish()

    @web.asynchronous
    def post(self):
        """Post requests are not supported."""
        pass

    def _get_active_nodes(self):
        result_dict = {'nodes': []}
        current_time = int(time.time())
        for ip, dt in self.application._nodes.items():
            if current_time < dt + options.max_time:
                result_dict['nodes'].append(ip)

        return result_dict


class NodesListener(object):
    """UDP listener class."""

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

        self._log.info('Nodes listener started, listening on port {0}'
                       .format(sock_addr[1]))

    def _open_and_register(self, af, sock_type, proto, sock_addr):
        sock = socket.socket(af, sock_type, proto)
        set_close_exec(sock.fileno())
        if os.name != 'nt':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
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
                self._log.info('Received "{0}" message from node "{1}"'
                               .format(data.decode().strip(), address[0]))

        self.io_loop.add_handler(sock.fileno(), read_handler, IOLoop.READ)
        self._sockets.append(sock)

    def stop(self):
        """Stop the UDP server."""
        self._log.debug('Closing %d socket(s)...', len(self._sockets))
        for sock in self._sockets:
            self.io_loop.remove_handler(sock.fileno())
            sock.close()


class RiotBrokerApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self):
        self._nodes = {}
        self._log = logging.getLogger("riot broker")
        handlers = [(r'/nodes', NodesProvider), ]
        settings = dict()
        super().__init__(handlers, **settings)
        self.listener = NodesListener('node listener', options.listener_port,
                                      on_receive=self.on_receive_packet)
        self._log.info('Nodes provider started, listening on port {0}'
                       .format(options.provider_port))

    def on_receive_packet(self, data, address):
        """Callback triggered when an alive packet is received."""
        self._nodes.update({address[0]: int(time.time())})


def parse_command_line():
    """Parse command line arguments for Riot broker application."""
    define("listener_port", default=8888, help="Node listener UDP port.")
    define("provider_port", default=8000, help="Node provider HTTP port")
    define("max_time", default=120, help="Retention time for lost nodes.")
    options.parse_command_line()


def main():
    """Entry point for RIOT broker application."""
    parse_command_line()
    try:
        app = RiotBrokerApplication()
        app.listen(options.provider_port)
        IOLoop.instance().start()
    except KeyboardInterrupt:
        print("Exiting")
        app.listener.stop()
        IOLoop.instance().stop()
        sys.exit()


if __name__ == '__main__':
    main()
