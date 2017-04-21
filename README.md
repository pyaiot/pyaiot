## A *Python for IoT* package connecting nodes to a web dashboard

Pyaiot provides a set of services to interact and transport data from IoT nodes
with regular web protocols (HTTP) and technologies. Pyaiot relies on Python
asyncio core module and on other more specific asyncio based packages such as
Tornado, Aiocoap.
Pyaiot tries to only use standard protocols and common practices to connect the
the web with the IoT nodes: CoAP, HTTP, etc

### The nodes

Pyaiot main objective is to provide high level services for communicating
with **constrained** nodes.
Those nodes are generally microcontroller based and generally not able to run
Linux. Thus, on those kind of nodes we need a specific OS. We choose
[RIOT](https://riot-os.org) because it provides an hardware independent layer
along with the standard network stacks required to communicate with the nodes.

The source code of the RIOT firmwares running on the nodes are available on
[another repository on GitHub](https://github.com/pyaiot/riot-firmwares).

### Available Demos

See Pyaiot in action within 2 demos:
* [RIOT](http://riot-os.org): You can find a permanent demo instance configured
  as a showroom for RIOT. This showroom is available at
  http://riot-demo.inria.fr.

* [IoT-LAB open A8 demo](utils/iotlab)
  This demo automatically submits an experiment on IoT-LAB with two open A8
  nodes. The first node is configured as a border router and the second node
  runs a firmware that integrates automatically in the RIOT Demo Dashboard
  described above.

### Broker and Dashboard services for an IoT dashboard

The broker manages a list of alive sensor nodes by running it's own CoAP
and WebSocket servers.

The Dashboard is a web page with some embeded javascript that displays the list
of available nodes and their status. It also allows to interact with the nodes
(LED control, Robot control, etc)

When a node starts, it notifies itself to the broker server by sending a CoAP
post. The broker then starts a discovery of the ressources provided by the node
(using the CoAP .well-known/core resource). Once the node available resources
are known, the broker sends to each web/mobile clients notification messages
so that they can update themselves.

To keep track of alive nodes, each node has to periodically send a notification
message to the broker.
If a sensor node has not sent this notification within 120s (default,
but this is configurable), the broker automatically removes it from the list
of alived nodes and notifies all web/mobile clients.

#### Installation procedure on a standalone system:

Here are the steps to install the IoT-Kit on a standalone system. The final
setup will be as follows:
* `aiot-broker` and `aiot-dashboard` running as systemd services
* the `aiot-broker` websocket server listening on port 8082
* the `aiot-dashboard` web application listening on port 8080. All served pages
  open a websocket client on the port 8082 of the broker

For a custom setup, please edit the `Environment` option of the
[aiot-broker](systemd/aiot-broker.service) and
[aiot-dashboard](systemd/aiot-dashboard.service) systemd service files
**before** deploying. The broker port should be the same in both service files
if you want the two to work together.

Here are the installation steps:

1. Clone this repository
<pre>
    $ git clone https://github.com/iot-lab/iot-kit.git
</pre>
2. Deploy the system (debian/raspbian/ubuntu):
<pre>
    $ make deploy
</pre>
3. Verify that the services are correctly running:
<pre>
    $ sudo systemctl status aiot-broker.service
    ● aiot-broker.service - Pyaiot Broker Application
       Loaded: loaded (/lib/systemd/system/aiot-broker.service; enabled)
       Active: active (running) since dim. 2016-12-18 14:59:56 CET; 35min ago
     Main PID: 32411 (python3)
       CGroup: /system.slice/aiot-broker.service
               └─32411 /usr/bin/python3 /usr/local/bin/aiot-broker --port=8082 --debug
    [...]
    $ sudo systemctl status aiot-dashboard.service
    ● aiot-dashboard.service - Pyaiot Dashboard Application
       Loaded: loaded (/lib/systemd/system/aiot-dashboard.service; enabled)
       Active: active (running) since dim. 2016-12-18 14:52:29 CET; 41min ago
     Main PID: 32321 (python3)
       CGroup: /system.slice/aiot-dashboard.service
               └─32321 /usr/bin/python3 /usr/local/bin/aiot-dashboard --port=8080 --broker-port=8082 --broker...
    [...]
</pre>

You can also
update `Environment` option in the services definition files **after**
deployment as they are locate in `/lib/systemd/system/aiot-broker.service` and
`/lib/systemd/system/aiot-dashboard.service`. In this case, you'all also need
to reload the systemd daemon services and restart the `aiot-broker` and
`aiot-dashboard` services:
```
    $ sudo systemctl daemon-reload
    $ sudo systemctl restart aiot-broker
    $ sudo systemctl restart aiot-dashboard
```

_**Example**_: Environments used in the online RIOT demo
* aiot-broker:
```
Environment='BROKER_PORT=8082'
```
* aiot-dashboard:
```
Environment='STATIC_PATH=/home/pi/demos/iotkit/dashboard/static' \
        'HTTP_PORT=8080' \
        'BROKER_PORT=80' \  # This is because the broker is behind an apache proxy
        'BROKER_HOST=riot-demo.inria.fr' \
        'APP_TITLE=RIOT Demo Dashboard' \
        'APP_LOGO=/static/assets/logo-riot.png' \
        'APP_FAVICON=/static/assets/favicon192.png'
```

#### Dashboard local development against an external IoT broker instance

Here we take as example the online demo available at http://riot-demo.inria.fr.
The websocket server of the broker service is reachable on port 80.
As the broker and the dashboard are decoupled in 2 distinct services,
it's possible to run a local dashboard application serving dashboard web page
that itself connects to the broker.
This way your dashboard will display the available nodes on the online RIOT
demo.

In this configuration, you don't need to install the `aiot-broker` and
`aiot-dashboard` services but you still need to install the required
development dependencies the first time:
```
    $ make install-dev
```

Then you can start the dashboard application:
```
    $ make run-dashboard
```
and open a web browser at [http://localhost:8080](http://localhost:8080).
When the web page is loaded, thanks to its embedded javascript, it directly
connects to the broker websocket server and starts to communicate with the
nodes.

Of course you can set the environment variables at your needs:
`BROKER_PORT`, `BROKER_HOST`, `DASHBOARD_PORT`, `DASHBOARD_TITLE`,
`DASHBOARD_LOGO`, `DASHBOARD_FAVICON`, `CAMERA_URL`.

```
    $ BROKER_PORT=8082 BROKER_HOST=localhost make run-dashboard
```

### Setting up a Raspberry PI with 802.15.4 as border router

A standalone IoT dashboard can run on a prepared raspberry pi:
* Hardware requirements:
  * OpenLABS 802.15.4 module installed an configured. See
    [this wiki page](https://github.com/RIOT-Makers/wpan-raspbian/wiki/Create-a-generic-Raspbian-image-with-6LoWPAN-support) for more information.
  * A RPI Camera installed and configured (optional)

* Software requirements:
  * Mjpg_streamer installed and running. See [the GitHub project.](https://github.com/jacksonliam/mjpg-streamer).

2 useful commands to manage custom raspbian images from Linux:
* Copy Raspberry PI SD to a compressed image on Linux:
```
    $ dd bs=4M if=/dev/mmcblk0 | gzip > custom_raspbian.img.gz
```
* Dump the compressed images to the Raspberry PI
```
    $ gzip -dc custom_raspbian.img.gz | sudo dd bs=4M of=/dev/mmcblk0
```

Then follow the IoT Dashboard installation steps described above.
