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
from tornado import gen, web, websocket
from tornado.websocket import websocket_connect

from pyaiot.common.auth import auth_token
from pyaiot.common.messaging import Message

logger = logging.getLogger("pyaiot.gw.ws")


class WebsocketNodeHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        """Allow connections from anywhere."""
        return True

    def open(self):
        """Discover nodes on each opened connection."""
        self.set_nodelay(True)
        logger.debug("New node websocket opened")

    @gen.coroutine
    def on_message(self, raw):
        """Triggered when a message is received from the web client."""
        message = Message.check_ws_message(self, raw)
        if message is not None:
            self.application.on_node_message(self, message)

    def on_close(self):
        """Remove websocket from internal list."""
        logger.debug("Node websocket closed")
        self.application.remove_ws(self)


class WebsocketGatewayApplication(web.Application):
    """Tornado based gateway application for websocket nodes on a network."""

    def __init__(self, keys, options=None):
        assert options

        self.keys = keys
        self.nodes = {}

        if options.debug:
            logger.setLevel(logging.DEBUG)

        handlers = [
            (r"/node", WebsocketNodeHandler),
        ]
        settings = {'debug': True}

        super().__init__(handlers, **settings)

        # Create connection to broker
        self.create_broker_connection(
            "ws://{}:{}/gw".format(options.broker_host, options.broker_port))

        logger.info('Application started, listening on port {}'
                    .format(options.gateway_port))

    @gen.coroutine
    def create_broker_connection(self, url):
        """Create an asynchronous connection to the broker."""
        while True:
            try:
                self.broker = yield websocket_connect(url)
            except ConnectionRefusedError:
                logger.debug("Cannot connect, retrying in 3s")
            else:
                logger.debug("Connected to broker, sending auth token")
                self.broker.write_message(auth_token(self.keys))
                while True:
                    message = yield self.broker.read_message()
                    if message is None:
                        logger.debug("Connection with broker lost.")
                        break
                    self.on_broker_message(message)

            yield gen.sleep(3)

    def send_to_broker(self, message):
        """Send a message to the parent broker."""
        if self.broker is not None:
            logger.debug("Forwarding message '{}' to parent broker."
                         .format(message))
            self.broker.write_message(message)

    def on_node_message(self, ws, message):
        """Handle a message received from a node websocket."""
        if message['type'] == "new":
            logger.debug("new node from websocket")
            self.nodes.update({ws: str(uuid.uuid4())})
            self.send_to_broker(
                Message.new_node(self.nodes[ws], 'websocket'))
        elif message['type'] == "update":
            if ws not in self.nodes:
                logger.debug("Node {} not in registered node".format(ws))
                return
            logger.debug("new update from node websocket")
            for key, value in message['data'].items():
                self.send_to_broker(
                    Message.update_node(self.nodes[ws], '/' + key, value))

    def on_broker_message(self, message):
        """Handle a message received from the parent broker websocket."""
        logger.debug("Handling message '{}' received from broker."
                     .format(message))
        message = json.loads(message)

        if message['type'] == "new":
            for node_ws, uid in self.nodes.items():
                self.broker.write_message(
                    Message.new_node(uid, 'websocket'))
                node_ws.write_message(Message.discover_node())
        elif message['type'] == "update":
            node = message['data']['node']
            for node_ws, uid in self.nodes.items():
                if uid == node:
                    node_ws.write_message(message['data'])

    def remove_ws(self, ws):
        """Remove websocket that has been closed."""
        if ws in self.nodes:
            self.send_to_broker(Message.out_node(self.nodes[ws]))
            self.nodes.pop(ws)
