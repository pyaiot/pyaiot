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

import uuid
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
        logger.info("New gateway websocket opened")

        # Wait 2 seconds to get the gateway authentication token.
        yield gen.sleep(2)
        if not self.authentified:
            self.close()

    @gen.coroutine
    def on_message(self, raw):
        """Triggered when a message is received from the broker child."""
        if not self.authentified:
            if verify_auth_token(raw, self.application.keys):
                logger.info("Gateway websocket authentication verified")
                self.authentified = True
                self.application.gateways.update({self: []})
            else:
                logger.info("Gateway websocket authentication failed, "
                            "closing.")
                self.close()
        else:
            message, reason = Message.check_message(raw)
            if message is not None:
                self.application.on_gateway_message(self, message)
            else:
                logger.debug("Invalid message, closing websocket")
                self.close(code=1003, reason="{}.".format(reason))

    def on_close(self):
        """Remove websocket from internal list."""
        logger.info("Gateway websocket closed")
        self.application.remove_ws(self)


class BrokerWebsocketClientHandler(websocket.WebSocketHandler):

    uid = None

    def check_origin(self, origin):
        """Allow connections from anywhere."""
        return True

    def open(self):
        """Discover nodes on each opened connection."""
        self.uid = str(uuid.uuid4())
        self.set_nodelay(True)
        logger.info("New client connection opened '{}'".format(self.uid))

    @gen.coroutine
    def on_message(self, raw):
        """Triggered when a message is received from the web client."""
        message, reason = Message.check_message(raw)
        if message is not None:
            message.update({'src': self.uid})
            self.application.on_client_message(self, message)
        else:
            logger.debug("Invalid message, closing websocket")
            self.close(code=1003, reason="{}.".format(reason))

    def on_close(self):
        """Remove websocket from internal list."""
        logger.info("Client connection closed '{}'".format(self.uid))
        self.application.remove_ws(self.uid)


class BrokerApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self, keys, options=None):
        assert options

        self.keys = keys
        self.gateways = {}
        self.clients = {}

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
        for uid in self.clients.keys():
            self.send_to_client(uid, message)

    def send_to_client(self, uid, message):
        """Send message to single client given its uid."""
        logger.debug("Sending message '{}' to client {}."
                     .format(message, uid))
        self.clients[uid].write_message(message)

    def on_client_message(self, ws, message):
        """Handle a message received from a client."""
        logger.debug("Handling message '{}' received from client websocket."
                     .format(message))
        if message['type'] == "new":
            logger.info("New client connected: {}".format(ws.uid))
            if ws.uid not in self.clients.keys():
                self.clients.update({ws.uid: ws})
        elif message['type'] == "update":
            logger.debug("New message from client: {}".format(ws.uid))

        # Simply forward this message to satellite gateways
        logger.debug("Forwarding message {} to gateways".format(message))
        for gw in self.gateways:
            gw.write_message(Message.serialize(message))

    @gen.coroutine
    def on_gateway_message(self, ws, message):
        """Handle a message received from a gateway.

        This method redirect messages from gateways to the right destinations:
        - for freshly new information initiated by nodes => broadcast
        - for replies to new client connection => only send to this client
        """
        logger.debug("Handling message '{}' received from gateway."
                     .format(message))
        if message['type'] == "new":
            # Received when notifying clients of a new node available
            if not message['uid'] in self.gateways[ws]:
                self.gateways[ws].append(message['uid'])

            if message['dst'] == "all":
                # Occurs when an unknown new node arrived
                self.broadcast(Message.serialize(message))
            elif message['dst'] in self.clients.keys():
                # Occurs when a single client has just connected
                self.send_to_client(
                    message['dst'], Message.serialize(message))
        elif (message['type'] == "out" and
                message['uid'] in self.gateways[ws]):
            # Node disparition are always broadcasted to clients
            self.gateways[ws].remove(message['uid'])
            self.broadcast(Message.serialize(message))
        elif (message['type'] == "update" and
                message['uid'] in self.gateways[ws]):
            if message['dst'] == "all":
                # Occurs when a new update was pushed by a node:
                # require broadcast
                self.broadcast(Message.serialize(message))
            elif message['dst'] in self.clients.keys():
                # Occurs when a new client has just connected:
                # Only the cached information of a node are pushed to this
                # specific client
                self.send_to_client(
                    message['dst'], Message.serialize(message))

    def remove_ws(self, ws):
        """Remove websocket that has been closed."""
        if ws in self.clients:
            self.clients.pop(ws)
        elif ws in self.gateways.keys():
            # Notify clients that the nodes behind the closed gateway are out.
            for node_uid in self.gateways[ws]:
                self.broadcast(Message.out_node(node_uid))
            self.gateways.pop(ws)
