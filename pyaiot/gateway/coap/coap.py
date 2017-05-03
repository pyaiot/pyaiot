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

"""CoAP management module."""

import time
import asyncio
import logging
import aiocoap.resource as resource

from tornado import gen
from aiocoap import Context, Message, GET, PUT, CHANGED

from pyaiot.common.messaging import Message as Msg

logger = logging.getLogger("pyaiot.gw.coap")


def _coap_endpoints(link_header):
    link = link_header.replace(' ', '')
    return link.split(',')


@gen.coroutine
def _coap_resource(url, method=GET, payload=b''):
    protocol = yield from Context.create_client_context()
    request = Message(code=method, payload=payload)
    request.set_request_uri(url)
    try:
        response = yield from protocol.request(request).response
    except Exception as e:
        code = "Failed to fetch resource"
        payload = '{0}'.format(e)
    else:
        code = response.code
        payload = response.payload.decode('utf-8')
    finally:
        yield from protocol.shutdown()

    logger.debug('Code: {0} - Payload: {1}'.format(code, payload))

    return code, payload


class CoapNode(object):
    """Object defining a CoAP node."""

    def __init__(self, address, check_time=time.time(), endpoints=[]):
        self.address = address
        self.check_time = check_time
        self.endpoints = endpoints

    def __eq__(self, other):
        return self.address == other.address

    def __neq__(self, other):
        return self.address != other.address

    def __repr__(self):
        return("Node '{}', Last check: {}, Endpoints: {}"
               .format(self.address, self.check_time, self.endpoints))


class CoapAliveResource(resource.Resource):
    """CoAP server running within the tornado application."""

    def __init__(self, controller):
        super(CoapAliveResource, self).__init__()
        self._controller = controller

    @asyncio.coroutine
    def render_post(self, request):
        payload = request.payload.decode('utf8')
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]
        logger.debug("CoAP Alive POST received from {}".format(remote))

        # Let the controller handle this message
        self._controller.handle_alive_message(remote)

        # Kindly reply the message has been processed
        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))


class CoapServerResource(resource.Resource):
    """CoAP server running within the tornado application."""

    def __init__(self, controller):
        super(CoapServerResource, self).__init__()
        self._controller = controller

    @asyncio.coroutine
    def render_post(self, request):
        payload = request.payload.decode('utf-8')
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]
        logger.debug("CoAP POST received from {} with payload: {}"
                     .format(remote, payload))

        if CoapNode(remote) in self._controller.nodes:
            path, data = payload.split(":", 1)
            self._controller.handle_post_message(
                Msg.update_node(remote, '/' + path, data))
        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))


class CoapController():
    """CoAP controller with CoAP server inside."""

    def __init__(self, on_message_cb, max_time=120):
        self._on_message_cb = on_message_cb
        self.max_time = max_time
        self.nodes = []
        self.setup()

    def setup(self):
        """Setup CoAP resources exposed by this server."""
        root_coap = resource.Site()
        root_coap.add_resource(('server', ),
                               CoapServerResource(self))
        root_coap.add_resource(('alive', ),
                               CoapAliveResource(self))
        asyncio.async(Context.create_server_context(root_coap))

    @gen.coroutine
    def discover_node(self, node):
        """Discover resources available on a node."""
        coap_node_url = 'coap://[{}]'.format(node.address)
        if len(node.endpoints) == 0:
            logger.debug("Discovering CoAP node {}".format(node.address))
            code, payload = yield _coap_resource('{0}/.well-known/core'
                                                 .format(coap_node_url),
                                                 method=GET)
            node.endpoints = _coap_endpoints(payload)

        messages = {}
        endpoints = [endpoint
                     for endpoint in node.endpoints
                     if 'well-known/core' not in endpoint]
        logger.debug("Fetching CoAP node resources: {}".format(endpoints))
        for endpoint in endpoints:
            elems = endpoint.split(';')
            path = elems.pop(0).replace('<', '').replace('>', '')

            try:
                code, payload = yield _coap_resource(
                    '{0}{1}'.format(coap_node_url, path), method=GET)
            except:
                logger.debug("Cannot discover ressource {} on node {}"
                             .format(endpoint, node.address))
                return
            messages[endpoint] = Msg.update_node(node.address, path, payload)

        logger.debug("Sending CoAP node resources: {}".format(endpoints))
        for endpoint in endpoints:
            self._on_message_cb(messages[endpoint])

    @gen.coroutine
    def send_data_to_node(self, data):
        """Forward received message data to the destination node.

        The message should be JSON and contain 'node', 'path' and 'payload'
        keys.

        - 'node' corresponds to the node address (generally IPv6)
        - 'path' corresponds to the CoAP resource on the node
        - 'payload' corresponds to the new payload for the CoAP resource.
        """
        node = data['node']
        path = data['path']
        payload = data['payload']
        logger.debug("Translating message ('{}') received to CoAP PUT "
                     "request".format(data))

        if CoapNode(node) not in self.nodes:
            return

        logger.debug("Updating CoAP node '{}' resource '{}'"
                     .format(node, path))
        code, payload = yield _coap_resource(
            'coap://[{0}]{1}'.format(node, path),
            method=PUT,
            payload=payload.encode('ascii'))

        return

    def handle_post_message(self, message):
        """Handle post message received from coap node."""
        self._on_message_cb(message)

    def handle_alive_message(self, node):
        """Handle alive message received from coap node."""
        node = CoapNode(node)
        node.check_time = time.time()
        if node not in self.nodes:
            self.nodes.append(node)
            self._on_message_cb(Msg.new_node(node.address, 'coap'))
            self.discover_node(node)
        else:
            index = self.nodes.index(node)
            self.nodes[index].check_time = time.time()

    def check_dead_nodes(self):
        """Check and remove nodes that are not alive anymore."""
        for node in self.nodes:
            if int(time.time()) > node.check_time + self.max_time:
                self.nodes.remove(node)
                logger.debug("Removing inactive node {}".format(node.address))
                self._on_message_cb(Msg.out_node(node.address))
