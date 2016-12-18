## Demos for RIOT

### Available Demos

* [IoT-LAB open A8
  demo](https://gitlab.inria.fr/fit-saclay/demos/tree/master/utils/iotlab)
  This demo automatically submit an experiment on IoT-LAB with two open A8
  nodes. The first node is configured as aborder router and the second node runs
  a firmware that integrates automatically on the RIOT Dashboard described
  below.


```
             _____   ___   _____     ___           _____           _          _      ____
            |  ___| |_ _| |_   _|   |_ _|   ___   |_   _|         | |        / \    | __ )
            | |_     | |    | |      | |   / _ \    | |    _____  | |       / _ \   |  _ \
            |  _|    | |    | |      | |  | (_) |   | |   |_____| | |___   / ___ \  | |_) |
            |_|     |___|   |_|     |___|  \___/    |_|           |_____| /_/   \_\ |____/
```

### Prerequisites for setting up a demonstration server

The Demos are designed to run on a prepared raspberry pi:
* Hardware requirements:
  * OpenLABS 802.15.4 module installed an configured. See
    [this wiki page](https://github.com/RIOT-Makers/wpan-raspbian/wiki/Create-a-generic-Raspbian-image-with-6LoWPAN-support) for more information.
  * A RPI Camera installed and configured
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

### Broker and Dashboard applications for RIOT demo

The broker manage a list of alive sensor nodes by running it's own CoAP
and WebSocket servers.

The Dashboard is a web page with some embeded javascript that display the list
of available nodes and their status. It also allows to interact with the nodes
(LED control, Robot control, etc)

When a node starts, it notifies itself the broker server by sending a CoAP
post the broker CoAP server. The broker then starts a discovery of the
available ressources provided by the node (using the CoAP .well-known/core
resource). Once the node available resources are known, the broker sends to
each web/mobile clients messages so that they can update themselves.

To keep track of alive nodes, each node has to periodically send a notification
message to the broker.
If a sensor node has not sent this notification within 60s, the broker removes
if from the list of alived nodes automatically and send a message to all
web/mobile clients.

#### Installation procedure:

1. Install the required packages:
<pre>
$ sudo pip3 install tornado aiocoap hbmqtt
</pre>
2. Clone this repository
<pre>
$ git clone git@gitlab.inria.fr:/fit-saclay/demos.git
</pre>
3. Setup the services:
<pre>
$ cd demos
$ make setup
</pre>
4. Verify the services are correctly running:
<pre>
$ sudo systemctl status riot-broker.service
● riot-broker.service - Riot Broker Application
   Loaded: loaded (/lib/systemd/system/riot-broker.service; enabled)
   Active: active (running) since dim. 2016-12-18 14:59:56 CET; 35min ago
 Main PID: 32411 (python3)
   CGroup: /system.slice/riot-broker.service
           └─32411 /usr/bin/python3 /home/pi/demos/broker/broker.py --port=8082 --debug
[...]
$ sudo systemctl status riot-dashboard.service
● riot-dashboard.service - Riot Dashboard Application
   Loaded: loaded (/lib/systemd/system/riot-dashboard.service; enabled)
   Active: active (running) since dim. 2016-12-18 14:52:29 CET; 41min ago
 Main PID: 32321 (python3)
   CGroup: /system.slice/riot-dashboard.service
           └─32321 /usr/bin/python3 /home/pi/demos/dashboard/dashboard.py --port=8080 --broker-port=80 --broker...
[...]
</pre>

#### Dashboard local development against http://riot-demo.inria.fr

A broker instance in running at http://riot-demo.inria.fr and its websocket
server is reachable on port 80. As the broker and the dashboard are
decoupled in 2 distinct services, it's possible to run a local dashboard
application serving dashboard web page that itself connect to the broker.
This way your dashboard will display the available nodes on the *real* demo.

To achieve this, at the root of the project, simply run:
```
$ make run-dashboard
```
and open a web browser at [http://localhost:8080](http://localhost:8080).

If want to display the *real* demo webcam, you can also use the `CAMERA_URL`
variable:
```
$ CAMERA_URL=http://riot-demo.inria.fr/demo-cam/?action=stream make run-dashboard
```
