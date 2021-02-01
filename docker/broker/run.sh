#!/bin/bash

: ${BROKER_HOST:=pyaiot-broker}
: ${BROKER_PORT:=8000}

aiot-broker --broker-host=${BROKER_HOST} --broker-port=${BROKER_PORT} \
            --debug
