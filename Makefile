
# Define default variables
PYTHON            ?= /usr/bin/python3
BROKER_PORT       ?= 80
BROKER_HOST       ?= riot-demo.inria.fr
DASHBOARD_PORT    ?= 8080
DASHBOARD_TITLE   ?= "RIOT Demo Dashboard"
DASHBOARD_LOGO    ?= /static/assets/logo-riot.png
DASHBOARD_FAVICON ?= /static/assets/favicon192.png
CAMERA_URL ?= /demo-cam/?action=stream

# Targets

setup: setup-broker setup-dashboard

setup-broker:
	sudo cp systemd/iot-broker.service /lib/systemd/system/.
	sudo systemctl enable iot-broker.service
	sudo systemctl daemon-reload
	sudo systemctl restart iot-broker.service

setup-dashboard:
	cd dashboard/static && npm install
	sudo cp systemd/iot-dashboard.service /lib/systemd/system/.
	sudo systemctl enable iot-dashboard.service
	sudo systemctl daemon-reload
	sudo systemctl restart iot-dashboard.service

run-broker:
	${PYTHON} broker/broker.py --port=${BROKER_PORT} --debug

run-dashboard:
	${PYTHON} dashboard/dashboard.py --port=${DASHBOARD_PORT}    \
		--broker-port=${BROKER_PORT} --broker-host=${BROKER_HOST}\
		--camera-url=${CAMERA_URL} --title=${DASHBOARD_TITLE}    \
		--logo=${DASHBOARD_LOGO} --favicon=${DASHBOARD_FAVICON}  \
		--debug
