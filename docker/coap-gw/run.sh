#!/bin/bash

: ${BROKER_HOST:=pyaiot-broker}
: ${BROKER_PORT:=8000}
: ${KEY_FILE:=}
: ${COAP_PORT:=5683}
: ${KEY_FILE:=}

aiot-coap-gateway --broker-host=${BROKER_HOST} --broker-port=${BROKER_PORT} \
                  --key-file=${KEY_FILE} --coap-port=${COAP_PORT} --debug
