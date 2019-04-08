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

MQTT_URL = 'mqtt://localhost:1886/'
NODE_ID = 'mqtt_test_node'
LED_VALUE = '0'
DELAY_CHECK = 30  # seconds


def pressure_value():
    return '{}°hPa'.format(random.randrange(990, 1015, 1))


NODE_RESOURCES = {'name': {'delay': 0,
                           'value': lambda x=None: "MQTT test node"},
                  'os': {'delay': 0,
                         'value': lambda x=None: "riot"},
                  'ip': {'delay': 0,
                         'value': (lambda x=None:
                                   socket.gethostbyname(
                                    socket.gethostname()))},
                  'board': {'delay': 0, 'value': lambda x=None: "HP"},
                  'led': {'delay': 0,
                          'value': lambda x=None: LED_VALUE},
                  'temperature': {'delay': 5,
                                  'value': (lambda x=None:
                                            '{}°C'
                                            .format(random.randrange(
                                                    20, 30, 1)))},
                  'pressure': {'delay': 10,
                               'value': (lambda x=None:
                                         '{}hPa'
                                         .format(random.randrange(
                                                 990, 1015, 1)))}
                  }


async def send_check(mqtt_client):
    while True:
        check_data = json.dumps({'id': NODE_ID})
        asyncio.get_event_loop().create_task(publish(
            mqtt_client, 'node/check', check_data))
        await asyncio.sleep(DELAY_CHECK)


def send_values(mqtt_client):
    for resource in NODE_RESOURCES:
        topic = 'node/{}/{}'.format(NODE_ID, resource)
        delay = NODE_RESOURCES[resource]['delay']
        value = NODE_RESOURCES[resource]['value']
        asyncio.get_event_loop().create_task(
            publish_continuous(mqtt_client, topic, value, delay))


async def start_client():
    """Connect to MQTT broker and subscribe to node check resource."""
    global __LED_VALUE__
    mqtt_client = MQTTClient()
    await mqtt_client.connect(MQTT_URL)
    # Subscribe to 'gateway/check' with QOS=1
    await mqtt_client.subscribe([('gateway/{}/discover'
                                  .format(NODE_ID), QOS_1)])
    await mqtt_client.subscribe([('gateway/{}/led/set'
                                  .format(NODE_ID), QOS_1)])
    asyncio.get_event_loop().create_task(send_check(mqtt_client))
    asyncio.get_event_loop().create_task(send_values(mqtt_client))
    while True:
        try:
            logger.debug("Waiting for incoming MQTT messages from gateway")
            # Blocked here until a message is received
            message = await mqtt_client.deliver_message()
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
                topic = 'node/{}/resources'.format(NODE_ID)
                value = json.dumps(list(NODE_RESOURCES.keys())).encode()
                asyncio.get_event_loop().create_task(
                    publish(mqtt_client, topic, value))
            else:
                for resource in NODE_RESOURCES:
                    topic = 'node/{}/{}'.format(NODE_ID, resource)
                    value = NODE_RESOURCES[resource]['value']
                    msg = json.dumps({'value': value()})
                    asyncio.get_event_loop().create_task(
                        publish(mqtt_client, topic, msg))
        elif topic_name.endswith("/led/set"):
            LED_VALUE = data
            topic = 'node/{}/led'.format(NODE_ID)
            data = json.dumps({'value': data}, ensure_ascii=False)
            asyncio.get_event_loop().create_task(
                publish(mqtt_client, topic, data.encode()))
        else:
            logger.debug("Topic not supported: {}".format(topic_name))


async def publish(mqtt_client, topic, value):
    if hasattr(value, 'encode'):
        value = value.encode()
    await mqtt_client.publish(topic, value, qos=QOS_1)
    logger.debug("Published '{}' to topic '{}'".format(value.decode(), topic))


async def publish_continuous(mqtt_client, topic, value, delay=0):
    while True:
        data = json.dumps({'value': value()}, ensure_ascii=False)
        await mqtt_client.publish(topic, data.encode('utf-8'), qos=QOS_1)
        logger.debug("Published '{}' to topic '{}'".format(data, topic))
        if delay == 0:
            break
        await asyncio.sleep(delay)


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    try:
        asyncio.get_event_loop().run_until_complete(start_client())
    except KeyboardInterrupt:
        logger.info("Exiting")
        asyncio.get_event_loop().stop()
