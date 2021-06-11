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

import logging
import time
import asyncio
import aiocoap.resource as resource

from tornado.ioloop import PeriodicCallback

from pyaiot.common.crypto import CryptoCtx
from aiocoap import Context, Message, GET, PUT, CHANGED
from aiocoap.numbers.codes import Code

from pyaiot.gateway.common import GatewayBase, Node
from . import initiator

logger = logging.getLogger("pyaiot.gw.coap")


COAP_PORT = 5683
MAX_TIME = 120

def _coap_endpoints(link_header):
    link = link_header.replace(' ', '')
    return link.split(',')


async def _coap_resource(url, method=GET, payload=b''):
    protocol = await Context.create_client_context()
    request = Message(code=method, payload=payload)
    request.set_request_uri(url)
    try:
        response = await protocol.request(request).response
    except Exception as exc:
        code = "Failed to fetch resource"
        payload = '{0}'.format(exc)
    else:
        code = response.code
        payload = response.payload.decode('utf-8')
    finally:
        await protocol.shutdown()

    logger.debug('Code: {0} - Payload: {1}'.format(code, payload))

    return code, payload


class CoapAliveResource(resource.Resource):
    """CoAP server running within the tornado application."""

    def __init__(self, gateway):
        super(CoapAliveResource, self).__init__()
        self._gateway = gateway

    async def render_post(self, request):
        """Triggered when a node post an alive check to the gateway."""
        payload = request.payload.decode('utf8')
        try:
            addr = request.remote[0]
        except TypeError:
            addr = request.remote.sockaddr[0]
        logger.debug("CoAP Alive POST received from {}".format(addr))

        # Let the controller handle this message
        uid = payload.split(':')[-1]
        await self._gateway.handle_coap_check(
            uid, addr, reset=(payload.startswith('reset')))

        # Kindly reply the message has been processed
        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))


class CoapServerResource(resource.Resource):
    """CoAP server running within the tornado application."""

    def __init__(self, gateway):
        super(CoapServerResource, self).__init__()
        self._gateway = gateway

    async def render_post(self, request):
        """Triggered when a node post a new value to the gateway."""
        payload = request.payload
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]
        try:
            node = self._gateway.get_node(self._gateway.node_mapping[remote])
            if node.has_crypto_ctx():
                try:
                    payload = node.ctx.decrypt_msg(payload)
                    logger.info("Decoded payload {}".format(payload))
                except:
                    logger.info("Unable to parse message")
                    payload = payload.decode('utf-8')
            else:
                payload = payload.decode('utf-8')
        except KeyError:
            pass

        logger.debug("CoAP POST received from {} with payload: {}"
                     .format(remote, payload))

        path, data = payload.split(":", 1)
        self._gateway.handle_coap_post(remote, path, data)

        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))


class CoapGateway(GatewayBase):
    """Tornado based gateway application for managing CoAP nodes."""

    PROTOCOL = 'CoAP'

    def __init__(self, keys, edhoc_keys, options):
        self.port = options.coap_port
        self.max_time = options.max_time
        self.interface = options.interface
        self.node_mapping = {}  # map node address to its uuid (TODO: FIXME)
        self.edhoc_keys = edhoc_keys

        super().__init__(keys, options)

        # Configure the CoAP server
        root_coap = resource.Site()
        root_coap.add_resource(('server', ),
                               CoapServerResource(self))
        root_coap.add_resource(('alive', ),
                               CoapAliveResource(self))
        asyncio.ensure_future(
            Context.create_server_context(root_coap, bind=('::', self.port)))

        # Start the periodic node cleanup task
        PeriodicCallback(self.check_dead_nodes, 1000).start()

        logger.info('CoAP gateway application started')


    async def edhoc_handshake(self, node, address):
        """Perform EDHOC handshake with node"""
        if not node.has_crypto_ctx():
            logger.info("Performing Handshake")
            salt, secret = await initiator.handshake(address,
                                                     self.edhoc_keys.authcred,
                                                     self.edhoc_keys.authkey)
            node.ctx.generate_aes_ccm_keys(salt, secret)
            logger.info("Handshake successfull")


    async def discover_node(self, node, handshake):
        """Discover resources available on a node."""
        address = node.resources['ip']
        if self.interface is not None:
            interface = '%{}'.format(self.interface)
        else:
            interface = ''
        coap_node_url = 'coap://[{}{}]'.format(address, interface)
        logger.info("Discovering CoAP node {}".format(address))
        _, payload = await _coap_resource('{0}/.well-known/core'
                                          .format(coap_node_url),
                                          method=GET)

        endpoints = [endpoint
                     for endpoint in _coap_endpoints(payload)
                     if 'well-known/core' not in endpoint]
        logger.debug("Fetching CoAP node resources: {}".format(endpoints))

        for endpoint in endpoints:
            elems = endpoint.split(';')
            path = elems.pop(0).replace('<', '').replace('>', '')
            if '/.well-known/edhoc' in endpoint and handshake:
                await self.edhoc_handshake(node, '[{}{}]'.format(address, interface))
            try:
                _, payload = await _coap_resource(
                    '{0}{1}'.format(coap_node_url, path), method=GET)
            except Exception:
                logger.debug("Cannot discover resource {} on node {}"
                             .format(endpoint, address))
                return

            if node.has_crypto_ctx():
                try:
                    payload = node.ctx.decrypt_msg(payload)
                except:
                    logger.info("Data is not encrypted")

            # Remove '/' from path
            self.forward_data_from_node(node, path[1:], payload)

        logger.debug("CoAP node resources '{}' sent to broker"
                     .format(endpoints))

    async def update_node_resource(self, node, endpoint, payload):
        """"""
        address = node.resources['ip']
        logger.debug("Updating CoAP node '{}' resource '{}'"
                     .format(address, endpoint))

        if node.has_crypto_ctx():
            payload = node.ctx.encrypt_msg(payload)

        code, _ = await _coap_resource(
            'coap://[{0}]/{1}'.format(address, endpoint),
            method=PUT,
            payload=payload.encode('utf-8'))
        if code == Code.CHANGED:
            self.forward_data_from_node(node, endpoint, payload)

    def handle_coap_post(self, address, endpoint, value):
        """Handle CoAP post message sent from coap node."""
        if address not in self.node_mapping:
            logger.debug("Unknown CoAP node '{}'".format(address))
            return
        node = self.get_node(self.node_mapping[address])
        self.forward_data_from_node(node, endpoint, value)

    async def handle_coap_check(self, uid, address, reset=False):
        """Handle check message received from coap node."""
        if uid not in self.node_mapping:
            # This is a totally new node: create uid, initialized cached node
            # send 'new' node notification, 'update' notification.
            node = Node(uid, ip=address)
            self.node_mapping.update({address: uid})
            await self.add_node(node)
        elif reset:
            # The data of the node need to be reset without removing it. This
            # is particularly the case after a reboot of the node or a
            # firmware update of the node that triggered the reboot.
            node = self.get_node(self.node_mapping[address])
            await self.reset_node(node, default_resources={'ip': address})
        else:
            # The node simply sent a check message to notify that it's still
            # online.
            node = self.get_node(self.node_mapping[address])
            node.update_last_seen()

    def check_dead_nodes(self):
        """Check and remove nodes that are not alive anymore."""
        to_remove = [node for node in self.nodes.values()
                     if int(time.time()) > node.last_seen + self.max_time]
        for node in to_remove:
            logger.info("Removing inactive node {}".format(node.uid))
            self.node_mapping.pop(node.resources['ip'])
            self.remove_node(node)
