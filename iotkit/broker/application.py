"""Broker application module."""

import json
import tornado
import logging

from tornado import gen, web, websocket

from .coap import _forward_message_to_node, _discover_node
from .data import coap_nodes, client_sockets
from .logger import logger


class BrokerPostHandler(web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, path=None):
        pass

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        """Forward POST request to a CoAP PUT request."""
        _forward_message_to_node(self.request.body.decode('utf-8'))


class BrokerWebsocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        """Allow connections from anywhere."""

        return True

    def open(self):
        """Discover nodes on each opened connection."""

        self.set_nodelay(True)
        logger.debug("New websocket opened")
        client_sockets.append(self)
        for node in coap_nodes:
            self.write_message(json.dumps({'command': 'new',
                                           'node': node.address}))
            _discover_node(node, self)

    @gen.coroutine
    def on_message(self, message):
        """Triggered when a message is received from the web client."""

        res = _forward_message_to_node(message, origin="Websocket")
        if res is not None:
            self.close(code=1003, reason=res)

    def on_close(self):
        """Remove websocket from internal list."""

        logger.debug("Websocket closed")
        if self in client_sockets:
            client_sockets.remove(self)


class BrokerApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self, options=None):
        self.options = options
        self._nodes = {}
        self._log = logger
        if self.options is not None and self.options.debug:
            self._log.setLevel(logging.DEBUG)

        handlers = [
            (r"/post", BrokerPostHandler),
            (r"/ws", BrokerWebsocketHandler),
        ]
        settings = {'debug': True,
                    'cookie_secret': 'MY_COOKIE_ID',
                    'xsrf_cookies': False}
        super().__init__(handlers, **settings)
        if self.options is not None:
            self._log.info('Application started, listening on port {0}'
                           .format(self.options.port))
