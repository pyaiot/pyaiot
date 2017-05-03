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
from tornado import gen, web, websocket

from pyaiot.common.auth import verify_auth_token
from pyaiot.common.messaging import Message

logger = logging.getLogger("pyaiot.broker")


class BrokerWebsocketGatewayHandler(websocket.WebSocketHandler):

    authentified = False

    def check_origin(self, origin):
        """Allow connections from anywhere."""
        return True

    @gen.coroutine
    def open(self):
        """Discover nodes on each opened connection."""
        self.set_nodelay(True)
        logger.debug("New gateway websocket opened")

        # Wait 2 seconds to get the gateway authentication token.
        yield gen.sleep(2)
        if not self.authentified:
            self.close()

    @gen.coroutine
    def on_message(self, raw):
        """Triggered when a message is received from the broker child."""
        if not self.authentified:
            if verify_auth_token(raw, self.application.keys):
                logger.debug("Gateway websocket authentication verified")
                self.authentified = True
                self.application.gateways.update({self: []})
            else:
                logger.debug("Gateway websocket authentication failed, "
                             "closing.")
                self.close()
        else:
            message = Message.check_ws_message(self, raw)
            if message is not None:
                self.application.on_gateway_message(self, message)

    def on_close(self):
        """Remove websocket from internal list."""
        logger.debug("Gateway websocket closed")
        self.application.remove_ws(self)


class BrokerWebsocketClientHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        """Allow connections from anywhere."""
        return True

    def open(self):
        """Discover nodes on each opened connection."""
        self.set_nodelay(True)
        logger.debug("New client websocket opened")

    @gen.coroutine
    def on_message(self, raw):
        """Triggered when a message is received from the web client."""
        message = Message.check_ws_message(self, raw)
        if message is not None:
            self.application.on_client_message(self, message)

    def on_close(self):
        """Remove websocket from internal list."""
        logger.debug("Client websocket closed")
        self.application.remove_ws(self)


class BrokerApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self, keys, options=None):
        assert options

        self.keys = keys
        self.gateways = {}
        self.clients = []

        if options.debug:
            logger.setLevel(logging.DEBUG)

        handlers = [
            (r"/ws", BrokerWebsocketClientHandler),
            (r"/gw", BrokerWebsocketGatewayHandler),
        ]
        settings = {'debug': True}

        super().__init__(handlers, **settings)
        logger.info('Application started, listening on port {}'
                    .format(options.port))

    def broadcast(self, message):
        """Broadcast message to all clients."""
        logger.debug("Broadcasting message '{}' to web clients."
                     .format(message))
        for ws in self.clients:
            ws.write_message(message)

    def on_client_message(self, ws, message):
        """Handle a message received from a client."""
        logger.debug("Handling message '{}' received from client websocket."
                     .format(message))
        if message['type'] == "new":
            logger.debug("new client connected")
            self.clients.append(ws)
        elif message['type'] == "update":
            logger.debug("new message from client websocket")

        # Simply forward this message to satellite gateways
        logger.debug("Forwarding message {} to gateways".format(message))
        for gw in self.gateways:
            gw.write_message(json.dumps(message))

    @gen.coroutine
    def on_gateway_message(self, ws, message):
        """Handle a message received from a gateway."""
        logger.debug("Handling message '{}' received from gateway."
                     .format(message))
        if (message['type'] == "new" and
                not message['node'] in self.gateways[ws]):
            self.gateways[ws].append(message['node'])
        elif (message['type'] == "out" and
                message['node'] in self.gateways[ws]):
            self.gateways[ws].remove(message['node'])

        self.broadcast(json.dumps(message))

    def remove_ws(self, ws):
        """Remove websocket that has been closed."""
        if ws in self.clients:
            self.clients.remove(ws)
        elif ws in self.gateways.keys():
            # Notify clients that the nodes behind the closed gateway are out.
            for node in self.gateways[ws]:
                self.broadcast(Message.out_node(node))
            self.gateways.pop(ws)
