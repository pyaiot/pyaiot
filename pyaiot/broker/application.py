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

logger = logging.getLogger("pyaiot.broker")


def _check_ws_message(ws, raw):
    """Verify a received message is correctly formatted."""
    reason = None
    try:
        message = json.loads(raw)
    except TypeError as e:
        logger.warning(e)
        reason = "Invalid message '{}'.".format(raw)
    except json.JSONDecodeError:
        reason = ("Invalid message received "
                  "'{}'. Only JSON format is supported.".format(raw))

    if 'type' not in message and 'data' not in message:
        reason = "Invalid message '{}'.".format(message)

    if message['type'] != 'new' and message['type'] != 'update':
        reason = "Invalid message type'{}'.".format(message['type'])

    if reason is not None:
        logger.warning(reason)
        ws.close(code=1003, reason="{}.".format(reason))
        message = None

    return message


class BrokerWebsocketGatewayHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        """Allow connections from anywhere."""
        return True

    def open(self):
        """Discover nodes on each opened connection."""
        self.set_nodelay(True)
        logger.debug("New gateway websocket opened")
        self.application.gateways.append(self)

    @gen.coroutine
    def on_message(self, message):
        """Triggered when a message is received from the broker child."""
        self.application.on_gateway_message(message)

    def on_close(self):
        """Remove websocket from internal list."""
        logger.debug("Broker websocket closed")
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
        message = _check_ws_message(self, raw)
        if message is not None:
            self.application.on_client_message(self, message)

    def on_close(self):
        """Remove websocket from internal list."""
        logger.debug("Client websocket closed")
        self.application.remove_ws(self)


class BrokerApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self, options=None):
        assert options

        self.gateways = []
        self.clients = []

        if options.debug:
            logger.setLevel(logging.DEBUG)

        handlers = [
            (r"/ws", BrokerWebsocketClientHandler),
            (r"/broker", BrokerWebsocketGatewayHandler),
        ]
        settings = {'debug': True}

        super().__init__(handlers, **settings)
        logger.info('Application started, listening on port {}'
                    .format(options.port))

    def broadcast(self, message):
        """Broadcast message to all opened websockets clients."""
        logger.debug("Broadcasting message '{}' to web clients."
                     .format(message))
        for ws in self.clients:
            ws.write_message(message)

    def on_client_message(self, ws, message):
        """Handle a message received from a client websocket."""
        logger.debug("Handling message '{}' received from client websocket."
                     .format(message))
        if message['type'] == "new":
            logger.debug("new client connected")
            self.clients.append(ws)
        elif message['type'] == "update":
            logger.debug("new update from client websocket")

        # Simply forward this message to satellite gateways
        for gw in self.gateways:
            logger.debug("Forwarding message {} to gateways".format(message))
            gw.write_message(json.dumps(message))

    @gen.coroutine
    def on_gateway_message(self, message):
        """Handle a message received from a gateway."""
        logger.debug("Handling message '{}' received from gateway."
                     .format(message))
        self.broadcast(message)

    def remove_ws(self, ws):
        """Remove websocket that has been closed."""
        if ws in self.clients:
            self.clients.remove(ws)
        elif ws in self.gateways:
            self.gateways.remove(ws)
