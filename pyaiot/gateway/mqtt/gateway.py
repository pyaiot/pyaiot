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

"""MQTT gateway module."""

import logging
import time
import uuid
import json
import asyncio

from tornado.ioloop import PeriodicCallback

from gmqtt import Client as MQTTClient

from pyaiot.gateway.common import Node, GatewayBase

logger = logging.getLogger("pyaiot.gw.mqtt")


MQTT_HOST = 'localhost'
MQTT_PORT = 1886
MAX_TIME = 120


class MQTTGateway(GatewayBase):
    """Gateway application for MQTT nodes on a network."""

    PROTOCOL = "MQTT"

    def __init__(self, keys, options):
        self.host = options.mqtt_host
        self.port = options.mqtt_port
        self.max_time = options.max_time
        self.options = options
        self.node_mapping = {}  # map node id to its uuid (TODO: FIXME)

        super().__init__(keys, options)

        # Connect to the MQTT broker
        self.mqtt_client= MQTTClient("client-id")

        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_message = on_message
        self.mqtt_client.on_disconnect = on_disconnect
        self.mqtt_client.on_subscribe = on_subscribe
     
        asyncio.get_event_loop().create_task(self.start())

        # Start the node cleanup task
        PeriodicCallback(self.check_dead_nodes, 1000).start()
        PeriodicCallback(self.request_alive, 30000).start()

        logger.info('MQTT gateway application started')

    async def start(self):
        await self.mqtt_client.connect('{}:{}'.format(self.host, self.port))

    def on_connect(self, client, flags, rc, properties):
        self.mqtt_client.subscribe('node/check', 1)

    def on_message(self, client, topic, payload, qos, properties):
        try:
            data = json.loads(payload)
        except Exception:
            # Skip data if not valid
            return
        logger.debug("Received message from node: {} => {}"
                     .format(topic, data))
        if topic.endswith("/check"):
            asyncio.get_event_loop().create_task(
                self.handle_node_check(data))
        elif topic.endswith("/resources"):
            asyncio.get_event_loop().create_task(
                self.handle_node_resources(topic, data))
        else:
            self.handle_node_update(topic, data)

    def on_disconnect(self, client, packet, exc=None):
        print('Disconnected')

    def on_subscribe(self, client, mid, qos, properties):
        print('SUBSCRIBED')

    def close(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._disconnect())

    async def _disconnect(self):
        for node in self.nodes:
            await self._disconnect_from_node(node)
        await self.mqtt_client.disconnect()

    async def discover_node(self, node):
        discover_topic = 'gateway/{}/discover'.format(node.resources['id'])
        await self.mqtt_client.publish(discover_topic, "resources", qos=1)
        logger.debug("Published '{}' to topic: {}"
                     .format("resources", discover_topic))

    def update_node_resource(self, node, endpoint, payload):
        node_id = node.resources['id']
        asyncio.get_event_loop().create_task(self.mqtt_client.publish(
            'gateway/{}/{}/set'.format(node_id, endpoint), payload, qos=1))

    async def handle_node_check(self, data):
        """Handle alive message received from coap node."""
        node_id = data['id']
        if node_id not in self.node_mapping:
            node = Node(str(uuid.uuid4()), id=node_id)
            self.node_mapping.update({node_id: node.uid})

            resources_topic = 'node/{}/resources'.format(node_id)
            await self.mqtt_client.subscribe(resources_topic, 1)
            logger.debug("Subscribed to topic: {}".format(resources_topic))

            self.add_node(node)
        else:
            # The node simply sent a check message to notify that it's still
            # online.
            node = self.get_node(self.node_mapping[node_id])
            node.update_last_seen()

    async def handle_node_resources(self, topic, data):
        """Process resources published by a node."""
        node_id = topic.split("/")[1]
        if node_id not in self.node_mapping:
            return

        await self.mqtt_client.subscribe(
            [('node/{}/{}'.format(node_id, resource), QOS_1)
             for resource in data])
        await self.mqtt_client.publish('gateway/{}/discover'
                                       .format(node_id), "values", qos=1)

    def handle_node_update(self, topic_name, data):
        """Handle CoAP post message sent from coap node."""
        _, node_id, resource = topic_name.split("/")
        value = data['value']
        if self.node_mapping[node_id] not in self.nodes:
            return

        node = self.get_node(self.node_mapping[node_id])
        self.forward_data_from_node(node, resource, value)

    def request_alive(self):
        """Publish a request to trigger a check publish from nodes."""
        logger.debug("Request check message from all MQTT nodes")
        asyncio.get_event_loop().create_task(
            self.mqtt_client.publish('gateway/check', '', qos=1))

    def check_dead_nodes(self):
        """Check and remove nodes that are not alive anymore."""
        to_remove = [node for node in self.nodes.values()
                     if int(time.time()) > node.last_seen + self.max_time]
        for node in to_remove:
            logger.info("Removing inactive node {}".format(node.uid))
            asyncio.get_event_loop().create_task(
                self._disconnect_from_node(node))
            self.node_mapping.pop(node.resources['id'])
            self.remove_node(node)

    async def _disconnect_from_node(self, node):
        node_id = node.resources['id']
        await self.mqtt_client.unsubscribe(
            ['node/{}/resource'.format(node_id)])
        for resource in node.resources:
            await self.mqtt_client.unsubscribe(
                ['node/{}/{}'.format(node_id, resource)])
