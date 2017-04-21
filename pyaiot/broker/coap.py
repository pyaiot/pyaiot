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
import json
import asyncio
import aiocoap.resource as resource

from tornado import gen, websocket
from aiocoap import Context, Message, GET, PUT, CHANGED

from .data import (coap_nodes, add_coap_node, remove_coap_node,
                   update_coap_node_check)
from .logger import logger
from .utils import _broadcast_message, _endpoints

_max_time = None


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


def _refresh_node(remote):
    """Refresh node last check or add it to the list of active nodes."""
    node = CoapNode(remote)
    node.check_time = time.time()
    nodes = coap_nodes()
    if node not in nodes:
        add_coap_node(node)
        _broadcast_message(json.dumps({'command': 'new',
                                       'node': node.address}))
        _discover_node(node)
    else:
        update_coap_node_check(node, time.time())


@gen.coroutine
def _discover_node(node, ws=None):
    """Callback functions called after fetching new nodes."""
    coap_node_url = 'coap://[{}]'.format(node.address)
    if len(node.endpoints) == 0:
        logger.debug("Discovering node {}".format(node.address))
        code, payload = yield _coap_resource('{0}/.well-known/core'
                                             .format(coap_node_url),
                                             method=GET)
        node.endpoints = _endpoints(payload)

    messages = {}
    endpoints = [endpoint
                 for endpoint in node.endpoints
                 if 'well-known/core' not in endpoint]
    for endpoint in endpoints:
        elems = endpoint.split(';')
        path = elems.pop(0).replace('<', '').replace('>', '')

        try:
            code, payload = yield _coap_resource('{0}{1}'
                                                 .format(coap_node_url, path),
                                                 method=GET)
        except:
            logger.debug("Cannot discover ressource {} on node {}"
                         .format(endpoint, node.address))
            return
        messages[endpoint] = json.dumps({'endpoint': path,
                                         'data': payload,
                                         'node': node.address,
                                         'command': 'update'})

    for endpoint in endpoints:
        message = messages[endpoint]
        if ws is None:
            _broadcast_message(message)
        else:
            try:
                ws.write_message(message)
            except websocket.WebSocketClosedError:
                logger.debug("Cannot write on a closed websocket.")


def _check_dead_nodes():
    """Find dead nodes in the list of known nodes and remove them."""
    nodes = coap_nodes()
    if len(nodes) == 0:
        return

    for node in nodes:
        if not node.active():
            remove_coap_node(node)
            logger.debug("Removing inactive node {}".format(node.address))
            _broadcast_message(json.dumps({'node': node.address,
                                           'command': 'out'}))


@gen.coroutine
def _forward_data_to_node(data, origin="POST"):
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
    logger.debug("Translating message ('{}') received from {} to CoAP PUT "
                 "request".format(data, origin))

    if CoapNode(node) not in coap_nodes():
        return
    code, payload = yield _coap_resource(
        'coap://[{0}]{1}'.format(node, path),
        method=PUT,
        payload=payload.encode('ascii'))

    return


def coap_server_init(max_time):
    """Initialize the CoAP server."""
    global _max_time
    _max_time = max_time

    root_coap = resource.Site()
    root_coap.add_resource(('server', ), CoapServerResource())
    root_coap.add_resource(('alive', ), CoapAliveResource())
    asyncio.async(Context.create_server_context(root_coap))


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

    def active(self):
        """check if the node is still active and responding."""
        if _max_time is None:
            return True

        return int(time.time()) < self.check_time + _max_time


class CoapAliveResource(resource.Resource):
    """CoAP server running within the tornado application."""

    def __init__(self):
        super(CoapAliveResource, self).__init__()

    @asyncio.coroutine
    def render_post(self, request):
        payload = request.payload.decode('utf8')
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]
        logger.debug("CoAP Alive POST received from {}".format(remote))

        _refresh_node(remote)

        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))


class CoapServerResource(resource.Resource):
    """CoAP server running within the tornado application."""

    def __init__(self):
        super(CoapServerResource, self).__init__()

    @asyncio.coroutine
    def render_post(self, request):
        payload = request.payload.decode('utf-8')
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]
        logger.debug("CoAP POST received from {} with payload: {}"
                     .format(remote, payload))

        if CoapNode(remote) in coap_nodes():
            path, data = payload.split(":", 1)
            _broadcast_message(json.dumps({'endpoint': '/' + path,
                                           'data': data,
                                           'node': remote,
                                           'command': 'update'}))
        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))
