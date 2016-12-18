
# Define default variables
PYTHON ?= /usr/bin/python3
BROKER_PORT ?= 80
BROKER_HOST ?= riot-demo.inria.fr
DASHBOARD_PORT ?= 8080
CAMERA_URL ?= /demo-cam/?action=stream

# Targets

setup: setup-broker setup-dashboard

setup-broker:
	sudo cp systemd/riot-broker.service /lib/systemd/system/.
	sudo systemctl enable riot-broker.service
	sudo systemctl daemon-reload
	sudo systemctl restart riot-broker.service

setup-dashboard:
	cd dashboard/static && npm install
	sudo cp systemd/riot-dashboard.service /lib/systemd/system/.
	sudo systemctl enable riot-dashboard.service
	sudo systemctl daemon-reload
	sudo systemctl restart riot-dashboard.service

run-broker:
	${PYTHON} broker/broker.py --port=${BROKER_PORT} --debug

run-dashboard:
	${PYTHON} dashboard/dashboard.py --port=${DASHBOARD_PORT} \
		--broker-port=${BROKER_PORT} --broker-host=${BROKER_HOST}\
		--camera-url=${CAMERA_URL}
		--debug
