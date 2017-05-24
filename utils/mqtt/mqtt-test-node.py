import json
import logging
import asyncio
import random
import socket

from hbmqtt.client import MQTTClient, ClientException
from hbmqtt.mqtt.constants import QOS_1

logging.basicConfig(format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')
logger = logging.getLogger("mqtt_test_node")

__MQTT_URL__ = 'mqtt://localhost:1886/'
__NODE_ID__ = 'mqtt_test_node'
__LED_VALUE__ = '0'
__DELAY_CHECK = 30  # seconds


def pressure_value():
    return '{}°hPa'.format(random.randrange(990, 1015, 1))


__NODE_RESOURCES__ = {'name': {'delay': 0,
                               'value': lambda x=None: "MQTT test node"},
                      'os': {'delay': 0,
                             'value': lambda x=None: "riot"},
                      'ip': {'delay': 0,
                             'value': (lambda x=None:
                                       socket.gethostbyname(
                                        socket.gethostname()))},
                      'board': {'delay': 0, 'value': lambda x=None: "HP"},
                      'led': {'delay': 0,
                              'value': lambda x=None: __LED_VALUE__},
                      'temperature': {'delay': 5,
                                      'value': (lambda x=None:
                                                '{}°C'
                                                .format(random.randrange(
                                                        20, 30, 1)))},
                      'pressure': {'delay': 10,
                                   'value': (lambda x=None:
                                             '{}°hPa'
                                             .format(random.randrange(
                                                     990, 1015, 1)))}
                      }


@asyncio.coroutine
def send_check(mqtt_client):
    while True:
        check_data = json.dumps({'id': __NODE_ID__})
        asyncio.ensure_future(publish(mqtt_client, 'node/check',
                                      check_data.encode()))
        yield from asyncio.sleep(__DELAY_CHECK)


@asyncio.coroutine
def start_client():
    """Connect to MQTT broker and subscribe to node ceck ressource."""
    global __LED_VALUE__
    mqtt_client = MQTTClient()
    yield from mqtt_client.connect(__MQTT_URL__)
    # Subscribe to 'gateway/check' with QOS=1
    yield from mqtt_client.subscribe([('gateway/{}/discover'
                                       .format(__NODE_ID__), QOS_1)])
    yield from mqtt_client.subscribe([('gateway/{}/led/set'
                                       .format(__NODE_ID__), QOS_1)])
    asyncio.ensure_future(send_check(mqtt_client))
    while True:
        try:
            logger.debug("Waiting for incoming MQTT messages from gateway")
            # Blocked here until a message is received
            message = yield from mqtt_client.deliver_message()
        except ClientException as ce:
            logger.error("Client exception: {}".format(ce))
            break
        except Exception as exc:
            logger.error("General exception: {}".format(exc))
            break
        packet = message.publish_packet
        topic_name = packet.variable_header.topic_name
        data = packet.payload.data.decode()
        logger.debug("Received message from gateway: {} => {}"
                     .format(topic_name, data))
        if topic_name.endswith("/discover"):
            if data == "resources":
                topic = 'node/{}/resources'.format(__NODE_ID__)
                value = json.dumps(list(__NODE_RESOURCES__.keys())).encode()
                asyncio.ensure_future(publish(mqtt_client, topic, value))
            else:
                for resource in __NODE_RESOURCES__:
                    topic = 'node/{}/{}'.format(__NODE_ID__, resource)
                    value = __NODE_RESOURCES__[resource]['value']
                    delay = __NODE_RESOURCES__[resource]['delay']
                    asyncio.ensure_future(
                        publish_continuous(mqtt_client, topic, value, delay))
        elif topic_name.endswith("/led/set"):
            __LED_VALUE__ = data
            topic = 'node/{}/led'.format(__NODE_ID__)
            data = json.dumps({'value': data})
            asyncio.ensure_future(publish(mqtt_client, topic, data.encode()))
        else:
            logger.debug("Topic not supported: {}".format(topic_name))


@asyncio.coroutine
def publish(mqtt_client, topic, value):
    yield from mqtt_client.publish(topic, value, qos=QOS_1)
    logger.debug("Published '{}' to topic '{}'".format(value, topic))


@asyncio.coroutine
def publish_continuous(mqtt_client, topic, value, delay=0):
    while True:
        data = json.dumps({'value': value()})
        yield from mqtt_client.publish(topic, data.encode(), qos=QOS_1)
        logger.debug("Published '{}' to topic '{}'".format(value(), topic))
        if delay == 0:
            break
        yield from asyncio.sleep(delay)


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    try:
        asyncio.get_event_loop().run_until_complete(start_client())
    except KeyboardInterrupt:
        logger.info("Exiting")
        asyncio.get_event_loop().stop()
