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

"""Base class for nodes controllers."""

import logging

from abc import ABCMeta, abstractmethod
from tornado import gen

from pyaiot.common.messaging import Message as Msg

logger = logging.getLogger("pyaiot.gw.common.nodes")


class NodesControllerBase(metaclass=ABCMeta):
    """Base nodes controller class."""

    def __init__(self, gateway):
        self._gateway = gateway
        self.nodes = {}

    @abstractmethod
    def send_data_to_node(self, data):
        """Forward received data to the destination node.

        :param data: A dict representing the data to send to the node.
                     This dict must have the 'uid', 'endpoint' and 'payload'
                     keys.
                    - 'uid': the node uid (uuid)
                    - 'endpoint': the name of the exposed resource on the node
                    - 'payload': the payload update of the endpoint
        """

    @gen.coroutine
    def send_message_to_broker(self, message):
        """Send a message to the broker via the gateway.

        :param message: the message to send as a string in JSON format

        .. seealso Message
        """
        self._gateway.send_to_broker(message)

    @gen.coroutine
    def fetch_nodes_cache(self, client):
        """Send cached nodes information to a given client.

        :param client: the ID of the client
        """
        logger.debug("Fetching cached information of registered nodes '{}'."
                     .format(self.nodes))
        for _, node in self.nodes.items():
            self.send_message_to_broker(Msg.new_node(node['uid'], dst=client))
            for resource, data in node['data'].items():
                self.send_message_to_broker(
                    Msg.update_node(node['uid'], resource, data, dst=client))
