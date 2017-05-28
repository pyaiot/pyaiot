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

"""Pyaiot messaging utility module."""

import json
import logging

logger = logging.getLogger("pyaiot.messaging")


class Message():
    """Utility class for generating and parsing service messages."""

    @staticmethod
    def serialize(message):
        return json.dumps(message, ensure_ascii=False)

    @staticmethod
    def new_node(uid, dst="all"):
        """Generate a text message indicating a new node."""
        return Message.serialize({'type': 'new', 'uid': uid, 'dst': dst})

    @staticmethod
    def out_node(uid):
        """Generate a text message indicating a node to remove."""
        return Message.serialize({'type': 'out', 'uid': uid})

    @staticmethod
    def update_node(uid, endpoint, data, dst="all"):
        """Generate a text message indicating a node update."""
        return Message.serialize({'type': 'update',
                                  'uid': uid,
                                  'endpoint': endpoint,
                                  'data': data,
                                  'dst': dst})

    @staticmethod
    def discover_node():
        """Generate a text message for websocket node discovery."""
        return Message.serialize({'request': 'discover'})

    @staticmethod
    def check_ws_message(ws, raw):
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

        if (message['type'] != 'new' and message['type'] != 'update' and
                message['type'] != 'out'):
            reason = "Invalid message type '{}'.".format(message['type'])

        if reason is not None:
            logger.warning(reason)
            ws.close(code=1003, reason="{}.".format(reason))
            message = None

        return message
