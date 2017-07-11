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

logger = logging.getLogger("pyaiot.gw.mqtt")


MQTT_HOST = 'localhost'
MQTT_PORT = 1886
MAX_TIME = 120
PROTOCOL = "MQTT"

class MQTTNode(object):
    """Object defining a MQTT node."""

    def __init__(self, identifier, check_time=time.time(), resources=[]):
        self.node_id = identifier
        self.check_time = check_time
        self.resources = resources

    def __eq__(self, other):
        return self.node_id == other.node_id

    def __neq__(self, other):
        return self.node_id != other.node_id

    def __hash__(self):
        return hash(self.node_id)

    def __repr__(self):
        return("Node '{}', Last check: {}, Resources: {}"
               .format(self.node_id, self.check_time, self.resources))


class MQTTController():
    """MQTT controller with MQTT client inside."""

    def __init__(self, on_message_cb, port=MQTT_PORT, max_time=MAX_TIME):
        # on_message_cb = send_to_broker method in gateway application
        self._on_message_cb = on_message_cb
        self.port = port
        self.max_time = max_time
        self.nodes = {}
        self.mqtt_client = MQTTClient()
        asyncio.get_event_loop().create_task(self.start())

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
        node = MQTTNode(node_id)
        node.check_time = time.time()
        if node not in self.nodes:
            resources_topic = 'node/{}/resources'.format(node_id)
            yield from self.mqtt_client.subscribe([(resources_topic, QOS_1)])
            logger.debug("Subscribed to topic: {}".format(resources_topic))
            node_uid = str(uuid.uuid4())
            self.nodes.update({node: {'uid': node_uid,
                                      'data': {'protocol': PROTOCOL}}})
            logger.debug("Available nodes: {}".format(self.nodes))
            self._on_message_cb(Msg.new_node(node_uid))
            self._on_message_cb(Msg.update_node(node_uid, "protocol", PROTOCOL))
            discover_topic = 'gateway/{}/discover'.format(node_id)
            yield from self.mqtt_client.publish(discover_topic, b"resources",
                                                qos=QOS_1)
            logger.debug("Published '{}' to topic: {}".format("resources",
                         discover_topic))
        else:
            data = self.nodes.pop(node)
            self.nodes.update({node: data})
        logger.debug("Available nodes: {}".format(self.nodes))

    @asyncio.coroutine
    def handle_node_resources(self, topic, data):
        """Process resources published by a node."""
        node_id = topic.split("/")[1]
        node = None
        for n in self.nodes.keys():
            if n.node_id == node_id:
                node = n
                break
        if node is None:
            return
        node.resources = data
        yield from self.mqtt_client.subscribe(
            [('node/{}/{}'.format(node_id, resource), QOS_1)
             for resource in data])
        yield from self.mqtt_client.publish('gateway/{}/discover'
                                            .format(node_id), b"values",
                                            qos=QOS_1)

    def handle_node_update(self, topic_name, data):
        """Handle CoAP post message sent from coap node."""
        _, node_id, resource = topic_name.split("/")
        node = MQTTNode(node_id)
        value = data['value']
        if node in self.nodes:
            if resource in self.nodes[node]['data']:
                # Add updated information to cache
                self.nodes[node]['data'][resource] = value
            else:
                self.nodes[node]['data'].update({resource: value})

        # Send update to broker
        self._on_message_cb(Msg.update_node(
            self.nodes[node]['uid'], resource, value))

    @gen.coroutine
    def fetch_nodes_cache(self, source):
        """Send cached nodes information."""
        logger.debug("Fetching cached information of registered nodes '{}'."
                     .format(self.nodes))
        for _, value in self.nodes.items():
            self._on_message_cb(Msg.new_node(value['uid'], dst=source))
            for resource, data in value['data'].items():
                self._on_message_cb(
                    Msg.update_node(value['uid'], resource, data,
                                    dst=source))

    def send_data_to_node(self, data):
        """Forward received message data to the destination node.

        The message should be JSON and contain 'uid', 'path' and 'payload'
        keys.

        - 'uid' corresponds to the node uid (uuid)
        - 'path' corresponds to the MQTT resource the node has subscribed to.
        - 'payload' corresponds to the new payload for the MQTT resource.
        """
        uid = data['uid']
        endpoint = data['endpoint']
        payload = data['payload']
        logger.debug("Translating message ('{}') received to MQTT publish "
                     "request".format(data))

        for node, value in self.nodes.items():
            if self.nodes[node]['uid'] == uid:
                node_id = node.node_id
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
        to_remove = [node for node in self.nodes.keys()
                     if int(time.time()) > node.check_time + self.max_time]
        for node in to_remove:
            asyncio.get_event_loop().create_task(
                self._disconnect_from_node(node))
            for resource in node.resources:
                pass
            uid = self.nodes[node]['uid']
            self.nodes.pop(node)
            logger.info("Removing inactive node {}".format(uid))
            logger.debug("Available nodes {}".format(self.nodes))
            self._on_message_cb(Msg.out_node(uid))

    @asyncio.coroutine
    def _disconnect_from_node(self, node):
        yield from self.mqtt_client.unsubscribe(
            ['node/{}/resource'.format(node.node_id)])
        for resource in node.resources:
            yield from self.mqtt_client.unsubscribe(
                ['node/{}/{}'.format(node.node_id, resource)])
