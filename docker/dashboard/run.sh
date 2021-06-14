#!/bin/bash

: ${BROKER_HOST:=localhost}
: ${BROKER_PORT:=8000}
: ${BROKER_SSL:=False}
: ${WEB_PORT:=8080}
: ${MAP_API_KEY:=invalid}
: ${KEY_FILE:=}
: ${STATIC_PATH:="/opt/pyaiot/pyaiot/dashboard/static"}
: ${CAMERA_URL:=}
: ${DASHBOARD_TITLE:="IoT Dashboard"}
: ${DASHBOARD_LOGO:="/static/assets/logo-riot.png"}
: ${DASHBOARD_FAVICON:="/static/assets/favicon192.png"}

aiot-dashboard --broker-host=${BROKER_HOST} --broker-port=${BROKER_PORT} \
                --web-port=${WEB_PORT} --broker-ssl=${BROKER_SSL} \
                --map-api-key=${MAP_API_KEY} --key-file=${KEY_FILE} \
                --static-path=/opt/pyaiot/pyaiot/dashboard/static \
                --camera-url=${CAMERA_URL} --title="${DASHBOARD_TITLE}" \
                --logo=${DASHBOARD_LOGO} --favicon=${DASHBOARD_FAVICON} \
                --debug
