
# Define default variables
STATIC_PATH       ?= ./pyaiot/dashboard/static/
BROKER_PORT       ?= 80
BROKER_HOST       ?= riot-demo.inria.fr
DASHBOARD_PORT    ?= 8080
DASHBOARD_TITLE   ?= "Local RIOT Demo Dashboard"
DASHBOARD_LOGO    ?= /static/assets/logo-riot.png
DASHBOARD_FAVICON ?= /static/assets/favicon192.png
CAMERA_URL ?= http://riot-demo.inria.fr/demo-cam/?action=stream

all: deploy
.PHONY: all

# Targets
deploy: install-dev setup-core-services

install-dev:
	wget -q -O - https://bootstrap.pypa.io/get-pip.py | sudo python3
	sudo apt-get install libyaml-dev libffi-dev libssl-dev npm -y
	sudo pip3 install .
	make setup-dashboard-npm

setup-core-services: setup-broker-service \
	setup-dashboard-service

aiot-broker.service:
	sudo cp systemd/aiot-broker.service /lib/systemd/system/.
	sudo systemctl enable aiot-broker.service
	sudo systemctl daemon-reload
	sudo systemctl restart aiot-broker.service
	sudo systemctl status aiot-broker.service

setup-broker-service: aiot-broker.service

aiot-coap-gateway.service:
	sudo cp systemd/aiot-coap-gateway.service /lib/systemd/system/.
	sudo systemctl enable aiot-coap-gateway.service
	sudo systemctl daemon-reload
	sudo systemctl restart aiot-coap-gateway.service
	sudo systemctl status aiot-coap-gateway.service

setup-coap-gateway-service: aiot-coap-gateway.service

aiot-ws-gateway.service:
	sudo cp systemd/aiot-ws-gateway.service /lib/systemd/system/.
	sudo systemctl enable aiot-ws-gateway.service
	sudo systemctl daemon-reload
	sudo systemctl restart aiot-ws-gateway.service
	sudo systemctl status aiot-ws-gateway.service

setup-ws-gateway-service: aiot-ws-gateway.service

.PHONY: setup-dashboard-npm
setup-dashboard-npm:
	cd pyaiot/dashboard/static && npm install

aiot-dashboard.service:
	sudo cp systemd/aiot-dashboard.service /lib/systemd/system/.
	sudo systemctl enable aiot-dashboard.service
	sudo systemctl daemon-reload
	sudo systemctl restart aiot-dashboard.service
	sudo systemctl status aiot-dashboard.service

setup-dashboard-service: setup-dashboard-npm aiot-dashboard.service

.PHONY: run-broker
run-broker:
	aiot-broker --port=${BROKER_PORT} --debug

.PHONY: run-coap-gateway
run-coap-gateway:
	aiot-coap-gateway --debug                                     \
		--broker-port=${BROKER_PORT} --broker-host=${BROKER_HOST}

.PHONY: run-ws-gateway
run-ws-gateway:
	aiot-ws-gateway --debug                                       \
		--broker-port=${BROKER_PORT} --broker-host=${BROKER_HOST} \
		--gateway-port=${BROKER_PORT}

.PHONY: run-dashboard
run-dashboard:
	aiot-dashboard --static-path=${STATIC_PATH}                   \
		--port=${DASHBOARD_PORT}                                  \
		--broker-port=${BROKER_PORT} --broker-host=${BROKER_HOST} \
		--camera-url=${CAMERA_URL} --title=${DASHBOARD_TITLE}     \
		--logo=${DASHBOARD_LOGO} --favicon=${DASHBOARD_FAVICON}   \
		--debug
