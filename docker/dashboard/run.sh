#!/bin/bash

: ${BROKER_HOST:=localhost}
: ${BROKER_PORT:=8000}
: ${BROKER_SSL}:=False}
: ${WEB_PORT:=8080}
: ${MAP_API_KEY}:=invalid}
: ${KEY_FILE}:=}

aiot-dashboard --broker-host=${BROKER_HOST} --broker-port=${BROKER_PORT} \
                --web-port=${WEB_PORT} --broker-ssl=${BROKER_SSL} \
                --map-api-key=${MAP_API_KEY} --key-file=${KEY_FILE} \
                --static-path=/opt/pyaiot/pyaiot/dashboard/static \
                --debug
