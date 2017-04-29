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

import logging
import json
import websocket as websocket_client

from tornado import gen

logger = logging.getLogger("pyaiot.gw.common")


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


class BrokerWebsocketClient():
    """Class for managing broker to broker connection via a websocket."""

    def __init__(self, controller, url, on_message_cb):
        self._on_message_cb = on_message_cb
        self._ws = None
        self.connect(url)
        if self._ws is not None:
            self._ws.message_cb = on_message_cb
            self._ws.on_message = BrokerWebsocketClient.on_message

    def connect(self, url):
        """Connect to parent broker."""
        try:
            self._ws = websocket_client.create_connection(url)
        except ConnectionRefusedError:
            logger.error("Cannot connect to websocket server at url '{}'"
                         .format(url))

    @gen.coroutine
    def write_message(self, message):
        """Send message to parent broker."""
        if self._ws is not None:
            self._ws.send(message)

    @staticmethod
    def on_message(ws, message):
        """Forward message to controller."""
        logger.debug("Message received from parent broker: {}".format(message))
        ws.message_cb(message)
