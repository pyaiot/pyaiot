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

"""CoAP gateway tornado application module."""

import json
import logging
from tornado.ioloop import PeriodicCallback
from tornado import web, gen
from tornado.websocket import websocket_connect

from pyaiot.common.auth import auth_token

from .coap import CoapController

logger = logging.getLogger("pyaiot.gw.coap")


class CoapGatewayApplication(web.Application):
    """Tornado based gateway application for CoAP nodes on a network."""

    def __init__(self, keys, options=None):
        assert options

        if options.debug:
            logger.setLevel(logging.DEBUG)

        self.broker = None
        self.keys = keys
        handlers = []
        settings = {'debug': True}

        # Starts CoAP controller
        self._coap_controllers = [
            CoapController(on_message_cb=self.send_to_broker,
                           port=options.coap_port,
                           max_time=options.max_time)
        ]

        if options.use_coaps:
            self._coap_controllers.append(
                CoapController(on_message_cb=self.send_to_broker,
                               port=options.coaps_port,
                               max_time=options.max_time,
                               dtls_enabled=options.use_coaps)
            )

        for controller in self._coap_controllers:
            PeriodicCallback(controller.check_dead_nodes, 1000).start()

        # NOTE: Starts a second CoAP (Secure) controller?

        # Create connection to broker
        self.create_broker_connection(
            "ws://{}:{}/gw".format(options.broker_host, options.broker_port))

        super().__init__(handlers, **settings)
        logger.info('CoAP gateway application started')

    def close_client(self):
        """Close client websocket"""
        logger.warning("CoAP controller: closing connection with broker.")
        self.broker.close()

    @gen.coroutine
    def create_broker_connection(self, url):
        """Create an asynchronous connection to the broker."""
        while True:
            try:
                self.broker = yield websocket_connect(url)
            except ConnectionRefusedError:
                logger.warning("Cannot connect, retrying in 3s")
            else:
                logger.info("Connected to broker, sending auth token")
                self.broker.write_message(auth_token(self.keys))
                yield gen.sleep(1)
                for controller in self._coap_controllers:
                    controller.fetch_nodes_cache('all')
                while True:
                    message = yield self.broker.read_message()
                    if message is None:
                        logger.warning("Connection with broker lost.")
                        break
                    self.on_broker_message(message)

            yield gen.sleep(3)

    @gen.coroutine
    def send_to_broker(self, message):
        """Send a message to the parent broker."""
        if self.broker is not None:
            logger.debug("Sending message '{}' to broker.".format(message))
            self.broker.write_message(message)

    def on_broker_message(self, message):
        """Handle a message received from the broker websocket."""
        logger.debug("Handling message '{}' received from broker."
                     .format(message))
        message = json.loads(message)

        if message['type'] == "new":
            # Received when a new client connects => fetching the nodes
            # in controller's cache
            for controller in self._coap_controllers:
                controller.fetch_nodes_cache(message['src'])
        elif message['type'] == "update":
            # Received when a client update a node
            for controller in self._coap_controllers:
                controller.send_data_to_node(message['data'])
