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
from ws4py.client.tornadoclient import TornadoWebSocketClient

logger = logging.getLogger("pyaiot.gw.common")


class BrokerWebsocketClient(TornadoWebSocketClient):
    """Class for managing broker to broker connection via a websocket."""

    def __init__(self, url, on_message_cb, on_disconnect):

        self._on_message_cb = on_message_cb
        self._on_disconnect = on_disconnect

        super().__init__(url, protocols=['http-only', 'chat'])

    def opened(self):
        """Handle websocket opening."""
        logger.debug("Gateway client websocket opened.")

    def received_message(self, message):
        """Handle incoming message."""
        logger.debug("Message received from broker: {}".format(message))
        yield from self._on_message_cb(message)

    def closed(self, code, reason=None):
        """Handle closed connection."""
        logger.debug("Gateway client websocket disconnected (code: {})."
                     .format(code))
        self._on_disconnect(reason)
