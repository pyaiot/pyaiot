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

"""Websocket nodes gateway module."""

import logging
import uuid
from tornado import gen, websocket

from pyaiot.common.messaging import Message
from pyaiot.gateway.common import GatewayBase, NodesControllerBase

logger = logging.getLogger("pyaiot.gw.ws")

PROTOCOL = "WebSocket"


class WebsocketNodeHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        """Allow connections from anywhere."""
        return True

    @gen.coroutine
    def open(self):
        """Discover nodes on each opened connection."""
        self.set_nodelay(True)
        logger.debug("New node websocket opened")
        self.application.nodes.update(
            {self: {'uid': str(uuid.uuid4()),
                    'data': {'protocol': PROTOCOL}}})
        node_uid = self.application.nodes[self]['uid']
        self.application.send_to_broker(Message.new_node(node_uid))
        yield self.write_message(Message.discover_node())
        self.application.send_to_broker(
            Message.update_node(node_uid, 'protocol', PROTOCOL))

    @gen.coroutine
    def on_message(self, raw):
        """Triggered when a message is received from the web client."""
        message, reason = Message.check_message(raw)
        if message is not None:
            self.application.on_node_message(self, message)
        else:
            logger.debug("Invalid message, closing websocket")
            self.close(code=1003, reason="{}.".format(reason))

    def on_close(self):
        """Remove websocket from internal list."""
        logger.debug("Node websocket closed")
        self.application.remove_ws(self)


class WebsocketGateway(GatewayBase, NodesControllerBase):
    """Gateway application for websocket nodes on a network."""

    def __init__(self, keys, options):
        if options.debug:
            logger.setLevel(logging.DEBUG)

        handlers = [
            (r"/node", WebsocketNodeHandler),
        ]

        GatewayBase.__init__(self, keys, options, handlers=handlers)
        NodesControllerBase.__init__(self, self)

        logger.info('WS gateway started, listening on port {}'
                    .format(options.gateway_port))

    def setup_nodes_controller(self):
        """Instantiate and configure a websocket nodes controller."""
        return self

    def on_node_message(self, ws, message):
        """Handle a message received from a node websocket."""
        if message['type'] == "update":
            logger.debug("New update message received from node websocket")
            for key, value in message['data'].items():
                if key in self.nodes[ws]['data']:
                    self.nodes[ws]['data'][key] = value
                else:
                    self.nodes[ws]['data'].update({key: value})
                self.send_to_broker(Message.update_node(
                    self.nodes[ws]['uid'], key, value))
        else:
            logger.debug("Invalid message received from node websocket")

    @gen.coroutine
    def send_data_to_node(self, data):
        """Forward received message data to the destination node."""
        uid = data['uid']
        for ws, value in self.nodes.items():
            if value['uid'] == uid:
                ws.write_message(data)

    def remove_ws(self, ws):
        """Remove websocket that has been closed."""
        if ws in self.nodes:
            self.send_to_broker(Message.out_node(self.nodes[ws]['uid']))
            self.nodes.pop(ws)
