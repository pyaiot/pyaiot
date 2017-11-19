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

"""MQTT management module."""

import time
import uuid
import json
import asyncio
import logging

from tornado import gen
from tornado.options import options

from hbmqtt.client import MQTTClient, ClientException
from hbmqtt.mqtt.constants import QOS_1

from pyaiot.common.messaging import Message as Msg
from pyaiot.gateway.common import NodesControllerBase, Node

logger = logging.getLogger("pyaiot.gw.mqtt")


MQTT_HOST = 'localhost'
MQTT_PORT = 1886
MAX_TIME = 120
PROTOCOL = "MQTT"


class MQTTNodesController(NodesControllerBase):
    """MQTT controller with MQTT client inside."""

    def __init__(self, gateway, port=MQTT_PORT, max_time=MAX_TIME):
        super().__init__(gateway)
        self.port = port
        self.max_time = max_time
        self.mqtt_client = MQTTClient()
        asyncio.get_event_loop().create_task(self.start())

        self.node_mapping = {}  # map node id to its uuid (TODO: FIXME)

    @asyncio.coroutine
    def start(self):
        """Connect to MQTT broker and subscribe to node check ressource."""
        yield from self.mqtt_client.connect('mqtt://{}:{}'
                                            .format(options.mqtt_host,
                                                    options.mqtt_port))
        # Subscribe to 'gateway/check' with QOS=1
        yield from self.mqtt_client.subscribe([('node/check', QOS_1)])
        while True:
            try:
                logger.debug("Waiting for MQTT messages published by nodes")
                # Blocked here until a message is received
                message = yield from self.mqtt_client.deliver_message()
            except ClientException as ce:
                logger.error("Client exception: {}".format(ce))
                break
            except Exception as exc:
                logger.error("General exception: {}".format(exc))
                break
            packet = message.publish_packet
            topic_name = packet.variable_header.topic_name
            try:
                data = json.loads(packet.payload.data.decode('utf-8'))
            except:
                # Skip data if not valid
                continue
            logger.debug("Received message from node: {} => {}"
                         .format(topic_name, data))
            if topic_name.endswith("/check"):
                asyncio.get_event_loop().create_task(
                    self.handle_node_check(data))
            elif topic_name.endswith("/resources"):
                asyncio.get_event_loop().create_task(
                    self.handle_node_resources(topic_name, data))
            else:
                self.handle_node_update(topic_name, data)

    def close(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._disconnect())

    @asyncio.coroutine
    def _disconnect(self):
        for node in self.nodes:
            yield from self._disconnect_from_node(node)
        yield from self.mqtt_client.disconnect()

    @asyncio.coroutine
    def handle_node_check(self, data):
        """Handle alive message received from coap node."""
        node_id = data['id']
        if node_id not in self.node_mapping:
            node = Node(str(uuid.uuid4()))
            self.node_mapping.update({node_id: node})

            resources_topic = 'node/{}/resources'.format(node_id)
            yield from self.mqtt_client.subscribe([(resources_topic, QOS_1)])
            logger.debug("Subscribed to topic: {}".format(resources_topic))

            self.nodes.update({node.uid: node})
            node.set_resource_value('protocol', PROTOCOL)
            node.set_resource_value('id', node_id)

            logger.debug("Available nodes: {}".format(self.nodes))
            self.send_message_to_broker(Msg.new_node(node.uid))
            for res, value in node.resources.items():
                self.send_message_to_broker(Msg.update_node(node.uid,
                                                            res, value))

            discover_topic = 'gateway/{}/discover'.format(node_id)
            yield from self.mqtt_client.publish(discover_topic, b"resources",
                                                qos=QOS_1)
            logger.debug("Published '{}' to topic: {}"
                         .format("resources", discover_topic))
        else:
            # The node simply sent a check message to notify that it's still
            # online.
            node = self.nodes[self.node_mapping[node_id]]
            node.update_last_seen()

        logger.debug("Available nodes: {}".format(self.nodes))

    @asyncio.coroutine
    def handle_node_resources(self, topic, data):
        """Process resources published by a node."""
        node_id = topic.split("/")[1]
        if self.node_mapping[node_id] not in self.nodes:
            return

        node = self.nodes[self.node_mapping[node_id]]
        node.resources.update(data)
        yield from self.mqtt_client.subscribe(
            [('node/{}/{}'.format(node_id, resource), QOS_1)
             for resource in data])
        yield from self.mqtt_client.publish('gateway/{}/discover'
                                            .format(node_id), b"values",
                                            qos=QOS_1)

    def handle_node_update(self, topic_name, data):
        """Handle CoAP post message sent from coap node."""
        _, node_id, resource = topic_name.split("/")
        value = data['value']
        if self.node_mapping[node_id] not in self.nodes:
            return

        node = self.nodes[self.node_mapping[node_id]]
        self.nodes[node.uid].set_resource_value(resource, value)

        # Send update to broker
        self.send_message_to_broker(Msg.update_node(node.uid, resource, value))

    def send_data_to_node(self, data):
        """Forward received data to the destination node."""
        uid = data['uid']
        endpoint = data['endpoint']
        payload = data['payload']
        logger.debug("Translating message ('{}') received to MQTT publish "
                     "request".format(data))

        for node_uid, node in self.nodes.items():
            if node_uid == uid:
                node_id = node.ressources['id']
                logger.debug("Updating MQTT node '{}' resource '{}'"
                             .format(node_id, endpoint))
                asyncio.get_event_loop().create_task(self.mqtt_client.publish(
                    'gateway/{}/{}/set'.format(node_id, endpoint),
                    payload.encode(), qos=QOS_1))
                break

    def request_alive(self):
        """Publish a request to trigger a check publish from nodes."""
        logger.debug("Request check message from all MQTT nodes")
        asyncio.get_event_loop().create_task(
            self.mqtt_client.publish('gateway/check', b'', qos=QOS_1))

    def check_dead_nodes(self):
        """Check and remove nodes that are not alive anymore."""
        to_remove = [node for node in self.nodes.values()
                     if int(time.time()) > node.last_seen + self.max_time]
        for node in to_remove:
            asyncio.get_event_loop().create_task(
                self._disconnect_from_node(node))
            self.node_mapping.pop(node.resources['id'])
            self.nodes.pop(node.uid)
            logger.info("Removing inactive node {}".format(node.uid))
            logger.debug("Available nodes {}".format(self.nodes))
            self.send_message_to_broker(Msg.out_node(node.uid))

    @asyncio.coroutine
    def _disconnect_from_node(self, node):
        node_id = node.resources['id']
        yield from self.mqtt_client.unsubscribe(
            ['node/{}/resource'.format(node_id)])
        for resource in node.resources:
            yield from self.mqtt_client.unsubscribe(
                ['node/{}/{}'.format(node_id, resource)])
