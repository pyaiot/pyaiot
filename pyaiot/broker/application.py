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
import logging
import uuid
from tornado.ioloop import PeriodicCallback
from tornado import gen, web, websocket

from .coap import CoapController
from .logger import logger


class BrokerWebsocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        """Allow connections from anywhere."""
        return True

    def open(self):
        """Discover nodes on each opened connection."""
        self.set_nodelay(True)
        logger.debug("New websocket opened")

    @gen.coroutine
    def on_message(self, raw):
        """Triggered when a message is received from the web client."""
        try:
            message = json.loads(raw)
        except TypeError as e:
            logger.warning(e)
            self.close(code=1003,
                       reason="Invalid message '{}'.".format(raw))
            return
        except json.JSONDecodeError:
            reason = ("Invalid message received "
                      "'{}'. Only JSON format is supported.".format(raw))
            logger.warning(reason)
            self.close(code=1003, reason="{}.".format(reason))
            return

        self.application.handle_ws_message(self, message)

    def on_close(self):
        """Remove websocket from internal list."""
        logger.debug("Websocket closed")
        self.application.remove_ws(self)


class BrokerApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self, options=None):
        self._options = options
        self._coap_controller = CoapController(
            on_message_cb=self.broadcast_to_clients,
            max_time=options.max_time)
        self.client_sockets = []
        self.node_sockets = {}
        self._log = logger
        if self._options is not None and self._options.debug:
            logger.setLevel(logging.DEBUG)

        handlers = [
            (r"/ws", BrokerWebsocketHandler),
        ]
        settings = {'debug': True,
                    'cookie_secret': 'MY_COOKIE_ID',
                    'xsrf_cookies': False}

        PeriodicCallback(self._coap_controller.check_dead_nodes, 1000).start()

        super().__init__(handlers, **settings)
        if self._options is not None:
            logger.info('Application started, listening on port {}'
                        .format(self._options.port))

    def broadcast_to_clients(self, message):
        """Broadcast message to all opened websockets clients."""
        logger.debug("Broadcasting message '{}' to web clients."
                     .format(message))
        for ws in self.client_sockets:
            ws.write_message(message)

    def handle_ws_message(self, ws, message):
        """Handle a message received from a websocket."""
        logger.debug("Handling message '{}' received from websocket."
                     .format(message))

        if 'type' not in message and 'data' not in message:
            ws.close(code=1003, reason="Invalid message '{}'.".format(message))

        if message['type'] == "new":
            if message['data'] == "client":
                logger.debug("new client connected")
                self.client_sockets.append(ws)
                for node in self._coap_controller.nodes:
                    ws.write_message(json.dumps({'command': 'new',
                                                 'node': node.address}))
                    self._coap_controller.discover_node(node)
                for node_ws, uid in self.node_sockets.items():
                    ws.write_message(json.dumps({'command': 'new',
                                                 'node': uid}))
                    node_ws.write_message(json.dumps({'request': 'discover'}))

            elif message['data'] == "node":
                logger.debug("new node from websocket")
                self.node_sockets.update({ws: str(uuid.uuid4())})
                self.broadcast_to_clients(
                    json.dumps({'command': 'new',
                                'node': self.node_sockets[ws]}))

        elif message['type'] == "update":
            if ws in self.client_sockets:
                logger.debug("new update from client websocket")
                self._coap_controller.send_data_to_node(message['data'])
            elif ws in self.node_sockets:
                logger.debug("new update from node websocket")
                for key, value in message['data'].items():
                    self.broadcast_to_clients(
                        json.dumps({'command': 'update',
                                    'node': self.node_sockets[ws],
                                    'endpoint': '/' + key,
                                    'data': value}))
        else:
            ws.close(code=1003, reason="Unknown message type '{}'."
                     .format(message['type']))

    def remove_ws(self, ws):
        """Remove websocket that has been closed."""
        if ws in self.client_sockets:
            self.client_sockets.remove(ws)
        elif ws in self.node_sockets:
            self.broadcast_to_clients(
                json.dumps({'node': self.node_sockets[ws],
                            'command': 'out'}))
            self.node_sockets.pop(ws)
