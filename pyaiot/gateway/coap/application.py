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
from tornado.ioloop import PeriodicCallback
from tornado import web, gen

from ..common.client import BrokerWebsocketClient
from .coap import CoapController

logger = logging.getLogger("pyaiot.gw.coap")


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


class CoapGatewayApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self, options=None):
        assert options

        if options.debug:
            logger.setLevel(logging.DEBUG)

        handlers = []
        settings = {'debug': True}

        # Connection to broker
        self.broker = BrokerWebsocketClient(
            "ws://{}:{}/broker".format(options.broker_host,
                                       options.broker_port),
            self.on_broker_message,
            self.on_broker_disconnect)
        self.broker.connect()

        # Starts CoAP controller
        self._coap_controller = CoapController(
            on_message_cb=self.send_to_broker,
            max_time=options.max_time)
        PeriodicCallback(self._coap_controller.check_dead_nodes, 1000).start()

        super().__init__(handlers, **settings)
        logger.info('CoAP gateway application started')

    def send_to_broker(self, message):
        """Send a message to the parent broker."""
        if self.broker is not None:
            logger.debug("Forwarding message '{}' to parent broker."
                         .format(message))
            self.broker.send(message)

    @gen.coroutine
    def on_broker_message(self, message):
        """Handle a message received from the parent broker websocket."""
        logger.warning("Handling message '{}' received from parent broker "
                       "websocket.".format(message))
        if message['type'] == "new":
            for node in self._coap_controller.nodes:
                self._coap_controller.discover_node(node)
        elif message['type'] == "update":
            self._coap_controller.send_data_to_node(message['data'])

    def on_broker_disconnect(self, reason=None):
        """Handle connection loss from broker."""
        logger.debug("Connection with broker lost, reason: '{}'."
                     .format(reason))
