#!/bin/bash

: ${BROKER_HOST:=localhost}
: ${BROKER_PORT:=8000}
: ${MAP_API_KEY}:=invalid}

aiot-dashboard --broker-host=${BROKER_HOST} --broker-port=${BROKER_PORT} \
                --map-api-key=${MAP_API_KEY} \
                --static-path=/opt/pyaiot/pyaiot/dashboard/static \
                --debug
