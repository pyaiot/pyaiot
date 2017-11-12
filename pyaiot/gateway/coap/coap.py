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
import uuid
import asyncio
import logging
import aiocoap.resource as resource

from tornado import gen
from aiocoap import Context, Message, GET, PUT, CHANGED
from aiocoap.numbers.codes import Code

from pyaiot.common.messaging import Message as Msg
from pyaiot.gateway.common import NodesControllerBase

logger = logging.getLogger("pyaiot.gw.coap")


COAP_PORT = 5683
MAX_TIME = 120
PROTOCOL = "CoAP"


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
    except Exception as exc:
        code = "Failed to fetch resource"
        payload = '{0}'.format(exc)
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

    def __hash__(self):
        return hash(self.address)

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
        """Triggered when a node post an alive check to the gateway."""
        payload = request.payload.decode('utf8')
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]
        logger.debug("CoAP Alive POST received from {}".format(remote))

        # Let the controller handle this message
        self._controller.handle_coap_check(remote, reset=(payload == 'reset'))

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
        """Triggered when a node post a new value to the gateway."""

        payload = request.payload.decode('utf-8')
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]
        logger.debug("CoAP POST received from {} with payload: {}"
                     .format(remote, payload))

        if CoapNode(remote) in self._controller.nodes.keys():
            path, data = payload.split(":", 1)
            self._controller.handle_coap_post(remote, path, data)
        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))


class CoapNodesController(NodesControllerBase):
    """CoAP nodes controller with a CoAP server inside."""

    def __init__(self, gateway, port=COAP_PORT, max_time=MAX_TIME):
        super().__init__(gateway)
        self.port = port
        self.max_time = max_time
        self.setup()

    def setup(self):
        """Setup CoAP resources exposed by this server."""
        root_coap = resource.Site()
        root_coap.add_resource(('server', ),
                               CoapServerResource(self))
        root_coap.add_resource(('alive', ),
                               CoapAliveResource(self))
        asyncio.async(
            Context.create_server_context(root_coap, bind=('::', self.port)))

    @gen.coroutine
    def discover_node(self, node, uid):
        """Discover resources available on a node."""
        coap_node_url = 'coap://[{}]'.format(node.address)
        if len(node.endpoints) == 0:
            logger.debug("Discovering CoAP node {}".format(node.address))
            _, payload = yield _coap_resource('{0}/.well-known/core'
                                              .format(coap_node_url),
                                              method=GET)
            node.endpoints = _coap_endpoints(payload)

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

            # Remove '/' from path
            path = path[1:]
            self.send_message_to_broker(Msg.update_node(uid, path, payload))
            self.nodes[node]['data'].update({path: payload})

        logger.debug("CoAP node resources '{}' sent to broker"
                     .format(endpoints))

    @gen.coroutine
    def send_data_to_node(self, data):
        """Forward received data to the destination node."""
        uid = data['uid']
        endpoint = data['endpoint']
        payload = data['payload']
        logger.debug("Translating message ('{}') received to CoAP PUT "
                     "request".format(data))

        for node, _ in self.nodes.items():
            if self.nodes[node]['uid'] == uid:
                address = self.nodes[node]['data']['ip']
                logger.debug("Updating CoAP node '{}' resource '{}'"
                             .format(self.nodes[node]['data']['ip'], endpoint))
                code, p = yield _coap_resource(
                    'coap://[{0}]/{1}'.format(address, endpoint),
                    method=PUT,
                    payload=payload.encode('ascii'))
                if code == Code.CHANGED:
                    self.nodes[node]['data'][endpoint] = payload
                    yield self.send_message_to_broker(
                        Msg.update_node(uid, endpoint, payload))
                break

    def handle_coap_post(self, address, endpoint, value):
        """Handle CoAP post message sent from coap node."""
        node = CoapNode(address)
        if node in self.nodes and endpoint in self.nodes[node]['data']:
            self.nodes[node]['data'][endpoint] = value
        self.send_message_to_broker(Msg.update_node(
            self.nodes[node]['uid'], endpoint, value))

    def handle_coap_check(self, address, reset=False):
        """Handle check message received from coap node."""
        node = CoapNode(address)
        node.check_time = time.time()
        if node not in self.nodes:
            # This is a totally new node: create uid, initialized cached node
            # send 'new' node notification, 'update' notification.
            node_uid = str(uuid.uuid4())
            self.nodes.update({node: {'uid': node_uid,
                                      'data': {'ip': address,
                                               'protocol': PROTOCOL}}})
            self.send_message_to_broker(Msg.new_node(node_uid))
            self.send_message_to_broker(Msg.update_node(node_uid,
                                                        "ip", address))
            self.send_message_to_broker(Msg.update_node(node_uid,
                                                        "protocol", PROTOCOL))
            self.discover_node(node, node_uid)
        elif reset:
            # The data of the node need to be reset without removing it. This
            # is particularly the case after a reboot of the node or a
            # firmware update of the node that triggered the reboot.
            node_uid = self.nodes[node]['uid']
            self.nodes[node]['data'] = {}
            self.nodes[node]['data'].update({'ip': address,
                                             'protocol': PROTOCOL})
            self.send_message_to_broker(Msg.reset_node(node_uid))
            self.discover_node(node, node_uid)
        else:
            # The node simply sent a check message to notify that it's still
            # online.
            data = self.nodes.pop(node)
            self.nodes.update({node: data})

    def check_dead_nodes(self):
        """Check and remove nodes that are not alive anymore."""
        to_remove = [node for node in self.nodes.keys()
                     if int(time.time()) > node.check_time + self.max_time]
        for node in to_remove:
            uid = self.nodes[node]['uid']
            self.nodes.pop(node)
            logger.info("Removing inactive node {}".format(uid))
            logger.debug("Available nodes {}".format(self.nodes))
            self.send_message_to_broker(Msg.out_node(uid))
