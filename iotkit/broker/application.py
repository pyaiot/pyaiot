# Copyright 2017 IoT-Lab Team
# Contributor(s) : see AUTHORS file
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Broker tornado application module."""

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
        for node in coap_nodes():
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
