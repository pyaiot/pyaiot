from network import WLAN
from umqtt import MQTTClient
import machine
import time
import json
import pycom


def settimeout(duration):
    pass

WIFI_PASS = ""
WIFI_SSID = ""

wlan = WLAN(mode=WLAN.STA)
wlan.antenna(WLAN.EXT_ANT)
wlan.connect(WIFI_SSID, auth=(WLAN.WPA2, WIFI_PASS), timeout=5000)

while not wlan.isconnected():
    machine.idle()

print("Connected to Wifi\n")
pycom.rgbled(0xff00)

LED_VALUE = '0'
LAT = 48.7144507
LNG = 2.2058228
NODE_ID = "wipy-1"
NODE_RESOURCES = dict(name="WiPy & MQTT", os="micropython", board="ESP8266",
                      position=json.dumps({'lat': LAT, 'lng': LNG}),
                      led=LED_VALUE)

client = MQTTClient("joe", "192.168.0.35", port=1886)


def publish_alive():
    global client
    global NODE_ID
    client.publish("node/check", json.dumps({'id': NODE_ID}))
    print('Alive published')


def publish_resources_list():
    global client
    global NODE_ID
    client.publish(topic='node/{}/resources'.format(NODE_ID),
                   msg=json.dumps(list(NODE_RESOURCES.keys())))


def publish_resources_values():
    global client
    global NODE_ID
    for resource, value in NODE_RESOURCES.items():
        print("Publishing resource '{}' with value '{}'"
              .format(resource, value))
        client.publish(topic='node/{}/{}'.format(NODE_ID, resource),
                       msg=json.dumps({'value': value}))
        time.sleep(1)


def publish_led_value():
    global client
    global NODE_ID
    global LED_VALUE
    print("Publishing led value '{}'".format(LED_VALUE))
    client.publish(topic='node/{}/led'.format(NODE_ID),
                   msg=json.dumps({'value': LED_VALUE}))


def sub_callback(topic, msg):
    global client
    global NODE_ID
    global LED_VALUE
    if topic == b'gateway/check':
        print("Reply alive")
        publish_alive()
    elif topic.endswith('discover'):
        if msg == b'resources':
            print("Reply resources")
            publish_resources_list()
        elif msg == b'values':
            print("Reply values")
            publish_resources_values()
        else:
            print("Unsupported message '{}'".format(msg))
    elif topic.endswith('led/set'):
        LED_VALUE = msg
        if int(msg):
            print("Turn on LED")
            pycom.rgbled(0x7f0000)
        else:
            print("Turn off LED")
            pycom.rgbled(0x000000)
        publish_led_value()
    else:
        print("Unsupported topic '{}'".format(topic))


client.set_callback(sub_callback)
client.connect()
client.subscribe(topic="gateway/{}/discover".format(NODE_ID))
client.subscribe(topic="gateway/check".format(NODE_ID))
client.subscribe(topic="gateway/{}/led/set".format(NODE_ID))
publish_alive()
pycom.rgbled(0x000000)
pycom.heartbeat(False)

while True:
    client.wait_msg()
