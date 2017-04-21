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
import uuid

from tornado import gen, web, websocket

from .coap import _forward_data_to_node, _discover_node
from .data import coap_nodes, client_sockets, node_sockets
from .logger import logger
from .utils import _broadcast_message


class BrokerPostHandler(web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, path=None):
        pass

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        """Forward POST request to a CoAP PUT request."""
        message = self.request.body.decode('utf-8')
        try:
            data = json.loads(message)
        except TypeError as e:
            logger.warning(e)
            return "{}".format(e)
        except json.JSONDecodeError:
            reason = ("Invalid message received "
                      "'{}'. Only JSON format is supported.".format(message))
            logger.warning(reason)
            return reason

        _forward_data_to_node(data['data'])


class BrokerWebsocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        """Allow connections from anywhere."""

        return True

    def open(self):
        """Discover nodes on each opened connection."""

        self.set_nodelay(True)
        logger.debug("New websocket opened")

    @gen.coroutine
    def on_message(self, message):
        """Triggered when a message is received from the web client."""
        try:
            data = json.loads(message)
        except TypeError as e:
            logger.warning(e)
            self.close(code=1003,
                       reason="Invalid message '{}'.".format(message))
            return
        except json.JSONDecodeError:
            reason = ("Invalid message received "
                      "'{}'. Only JSON format is supported.".format(message))
            logger.warning(reason)
            self.close(code=1003, reason="{}.".format(reason))
            return

        if 'type' not in data and 'data' not in data:
            self.close(code=1003,
                       reason="Invalid message '{}'.".format(message))

        if data['type'] == "new":
            if data['data'] == "client":
                client_sockets.append(self)
                for node in coap_nodes():
                    self.write_message(json.dumps({'command': 'new',
                                                   'node': node.address}))
                    _discover_node(node, self)
                for ws, uid in node_sockets.items():
                    self.write_message(json.dumps({'command': 'new',
                                                   'node': uid}))
                    ws.write_message(json.dumps({'request': 'discover'}))

            elif data['data'] == "node":
                node_sockets.update({self: str(uuid.uuid4())})
                _broadcast_message(json.dumps({'command': 'new',
                                               'node': node_sockets[self]}))
        elif data['type'] == "update":
            if self in client_sockets:
                _forward_data_to_node(data['data'], origin="Websocket")
            elif self in node_sockets:
                for key, value in data['data'].items():
                    _broadcast_message(
                        json.dumps({'command': 'update',
                                    'node': node_sockets[self],
                                    'endpoint': '/' + key,
                                    'data': value}))
        else:
            self.close(code=1003,
                       reason="Unknown message type '{}'.".format(
                              data['type']))

    def on_close(self):
        """Remove websocket from internal list."""

        logger.debug("Websocket closed")
        if self in client_sockets:
            client_sockets.remove(self)
        elif self in node_sockets:
            _broadcast_message(json.dumps({'node': node_sockets[self],
                                           'command': 'out'}))
            node_sockets.pop(self)


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
