## An IoT Dashboard for open and great IoT demos

### Available Demos

* [RIOT](http://riot-os.org): You can find a permanent demo instance configured
  as a showroom for RIOT. This showroom is available at
  http://riot-demo.inria.fr.

* [IoT-LAB open A8 demo](utils/iotlab)
  This demo automatically submits an experiment on IoT-LAB with two open A8
  nodes. The first node is configured as a border router and the second node
  runs a firmware that integrates automatically in the RIOT Demo Dashboard
  described above.

```
             _____   ___   _____     ___           _____           _          _      ____
            |  ___| |_ _| |_   _|   |_ _|   ___   |_   _|         | |        / \    | __ )
            | |_     | |    | |      | |   / _ \    | |    _____  | |       / _ \   |  _ \
            |  _|    | |    | |      | |  | (_) |   | |   |_____| | |___   / ___ \  | |_) |
            |_|     |___|   |_|     |___|  \___/    |_|           |_____| /_/   \_\ |____/
```

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
* `iot-broker` and `iot-dashboard` running as systemd services
* the `iot-broker` websocket server listening on port 8082
* the `iot-dashboard` web application listening on port 8080. All served pages
  open a websocket client on the port 8082 of the broker

For a custom setup, please edit the `Environment` option of the
[iot-broker](systemd/iot-broker.service) and
[iot-dashboard](systemd/iot-dashboard.service) systemd service files
**before** deploying. The broker port should be the same in both service files
if you want the two to work together.

1. Install the iot-kit package from the source:
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
    $ sudo systemctl status iot-broker.service
    ● iot-broker.service - IoT Broker Application
       Loaded: loaded (/lib/systemd/system/iot-broker.service; enabled)
       Active: active (running) since dim. 2016-12-18 14:59:56 CET; 35min ago
     Main PID: 32411 (python3)
       CGroup: /system.slice/riot-broker.service
               └─32411 /usr/bin/python3 /home/pi/demos/bin/iot-broker --port=8082 --debug
    [...]
    $ sudo systemctl status iot-dashboard.service
    ● iot-dashboard.service - IoT Dashboard Application
       Loaded: loaded (/lib/systemd/system/iot-dashboard.service; enabled)
       Active: active (running) since dim. 2016-12-18 14:52:29 CET; 41min ago
     Main PID: 32321 (python3)
       CGroup: /system.slice/iot-dashboard.service
               └─32321 /usr/bin/python3 /home/pi/demos/bin/iot-dashboard --port=8080 --broker-port=8082 --broker...
    [...]
</pre>

You can also
update `Environment` option in the services definition files after deployment
as they are locate in `/lib/systemd/system/iot-broker.service` and
`/lib/systemd/system/iot-dashboard.service`. In this case, you'all also need
to reload the systemd daemon services and restart the `iot-broker` and
`iot-dashboard` services:
```
    $ sudo systemctl daemon-reload
    $ sudo systemctl restart iot-broker
    $ sudo systemctl restart iot-dashboard
```

_**Example**_: Environments used in the online RIOT demo
* iot-broker:
```
Environment='BROKER_PORT=8082'
```
* iot-dashboard:
```
Environment='HTTP_PORT=8080' \
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

In this configuration, you don't need to install the iot-broker and
iot-dashboard services but you still need to install the required development
dependencies the first time:
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
