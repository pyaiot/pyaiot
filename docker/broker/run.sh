#!/bin/bash

: ${BROKER_HOST:=pyaiot-broker}
: ${BROKER_PORT:=8000}
: ${KEY_FILE:="/home/${USER}/.pyaiot"}

aiot-broker --broker-host=${BROKER_HOST} --broker-port=${BROKER_PORT} \
            --key-file=${KEY_FILE} --debug
