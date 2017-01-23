## An IoT Dashboard for open and great IoT demos

### Available Demos

* [RIOT](http://riot-os.org): You can find a permanent demo instance configured
  as a showroom for RIOT. This showroom is available at
  http://riot-demo.inria.fr.

* [IoT-LAB open A8
  demo](https://gitlab.inria.fr/fit-saclay/demos/tree/master/utils/iotlab)
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

### Broker and Dashboard applications for an IoT dashboard

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

#### Installation procedure:

1. Install the iot-kit package from the source:
  1. Clone this repository
<pre>
$ git clone git@gitlab.inria.fr:/fit-saclay/demos.git
</pre>
  2. Install with pip as user
<pre>
$ cd demos
$ pip install -e .
</pre>
3. Setup the services:
<pre>
$ make setup
</pre>
4. Verify the services are correctly running:
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
           └─32321 /usr/bin/python3 /home/pi/demos/bin/iot-dashboard --port=8080 --broker-port=80 --broker...
[...]
</pre>

#### Dashboard local development against your IoT broker instance

Here we assume that you have an IoT broker instance running and available at
http://broker.instance.org. Its websocket server is reachable on port 80.
As the broker and the dashboard are decoupled in 2 distinct services,
it's possible to run a local dashboard application serving dashboard web page
that itself connect to the broker.
This way your dashboard will display the available nodes on the *real* demo.

To achieve this, at the root of the project, simply run:
```
$ make run-dashboard
```
and open a web browser at [http://localhost:8080](http://localhost:8080).

### Setting up a standalone IoT dashboard on a Raspberry PI

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
