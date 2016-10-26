## Demos for the FIT IoT-LAB testbed in Saclay

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


### Broker application for RIOT demo

The broker manage a list of alive sensor nodes by listening on an UDP port.
The list of alive nodes can be retrieved using HTTP from any host on a
network.

By default, the UDP port is listening on port 8888 and HTTP url is
`http://<your_broker_host>:8000/nodes`

The alive nodes are retrieved in the following json format:
{ 'node':
 [ ip1, ip2, ip3]
}

If a sensor node has not sent a update within 60s, it's removed from the
list of alived nodes automatically.

#### Installation procedure:

1. Install the required packages:
<pre>
$ sudo pip3 install tornado
</pre>
2. Copy the systemd service file:
<pre>
$ sudo cp systemd/riot-broker.service /lib/systemd/system/.
</pre>
3. Enable it and start it:
<pre>
$ sudo systemctl enable riot-broker.service
$ sudo systemctl start riot-broker.service
</pre>
4. Verify it's correctly running:
<pre>
$ sudo systemctl status riot-broker.service
● riot-broker.service - Riot Broker Application
   Loaded: loaded (/lib/systemd/system/riot-broker.service; enabled)
   Active: active (running) since Tue 2016-10-25 08:51:02 UTC; 4min 55s ago
 Main PID: 1469 (python3)
   CGroup: /system.slice/riot-broker.service
           └─1469 /usr/bin/python3 /home/pi/demos/riot-broker.py
Oct 25 08:51:37 raspberrypi python3[1469]: 2016-10-25 08:51:37,844 - tornado...s
Oct 25 08:51:37 raspberrypi python3[1469]: 2016-10-25 08:51:37,875 - tornado...s
Oct 25 08:52:01 raspberrypi python3[1469]: [124B blob data]
Oct 25 08:52:31 raspberrypi python3[1469]: [124B blob data]
Oct 25 08:53:01 raspberrypi python3[1469]: [124B blob data]
Oct 25 08:53:31 raspberrypi python3[1469]: [124B blob data]
Oct 25 08:54:01 raspberrypi python3[1469]: [124B blob data]
Oct 25 08:54:31 raspberrypi python3[1469]: [124B blob data]
Oct 25 08:55:01 raspberrypi python3[1469]: [124B blob data]
Oct 25 08:55:31 raspberrypi python3[1469]: [124B blob data]
Hint: Some lines were ellipsized, use -l to show in full.
</pre>


### RIOT Dashboard

The dashboard displays the values of CoAP endpoints discovered on the known
nodes. It also allows to interact with CoAP endpoints providing `PUT` requests.

#### Installation procedure

1. Install the latest nodejs version:
<pre>
$ curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
$ sudo apt install -y nodejs
</pre>
2. Install required node packages:
<pre>
$ cd dashboard
$ npm install
</pre>
3. Copy the systemd service file:
<pre>
$ sudo cp systemd/riot-dashboard.service /lib/systemd/system/.
</pre>
4. Enable it and start it:
<pre>
$ sudo systemctl enable riot-dashboard.service
$ sudo systemctl start riot-dashboard.service
</pre>
5. Verify it's correctly running:
<pre>
$ sudo systemctl status riot-dashboard.service
● riot-dashboard.service - Riot Dashboard Application
   Loaded: loaded (/lib/systemd/system/riot-dashboard.service; enabled)
   Active: active (running) since Tue 2016-10-25 11:19:57 CEST; 5s ago
 Main PID: 7398 (node)
   CGroup: /system.slice/riot-dashboard.service
           └─7398 /usr/bin/node /home/pi/demos/dashboard/dashboard.js
Oct 25 11:19:57 raspberrypi systemd[1]: Started Riot Dashboard Application.
Oct 25 11:20:02 raspberrypi node[7398]: Web server running at http://[::1]:8080
Hint: Some lines were ellipsized, use -l to show in full.
</pre>


