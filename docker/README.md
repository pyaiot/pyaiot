### Docker containers for Pyaiot

Docker containers are provided for an easy and minimal setup of the different
Pyaiot services: pyaiot/broker, pyaiot/dashboard and pyaiot/coap-gw.

### Usage

To start all services in one command, use docker-compose:

```
docker-compose -f docker/docker-compose.yml up
```

This starts the broker, dashboard and coap gateway services locally on the
host machine:
- the dashboard is available at **http://localhost:8080**
- the broker listens to incoming websocket connections on port **8000**
- the coap gateway listens to incoming CoAP request on port **5684/udp**

To stop the services **use Ctrl+C twice**.

### Testing the setup

When the services are running locally with docker-compose, the setup can be
tested using the utility Python test script:

```
python3 utils/coap/coap-test-node.py --gateway-port=5684 --temperature --imu
```

If everything works, the `Python Test Node` should appear and push data on the
web dashboard.
