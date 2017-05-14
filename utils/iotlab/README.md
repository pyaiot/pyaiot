## IoTLAB demo script

Here is a script that automatizes the deployment of demonstration nodes on
IoT-LAB. This README explains how to setup your environment and how to run
the script.

The `iotlab-launch-demo` script will book several A8 nodes on the IoT-LAB testbed
in Saclay site. One of the node is configured as a border router, the other ones
are running the demonstration firmware `dashboard_riot_a8_m3.elf`.

You need an IoT-LAB account to run this script.

#### Requirements

1. Install the IoT-LAB ssh-cli-tools package:
<pre>
$ sudo pip install iotlabsshcli
</pre>
2. Play at least once the [RIOT border router tutorial on IoT-LAB
   portal](https://www.iot-lab.info/tutorials/riot-public-ipv66lowpan-network-with-a8-m3-nodes/)
   Important: use the same directories on the Saclay site ssh frontend
3. Clone this repository:
<pre>
$ git clone https://github.com/pyaiot/payiot.git
</pre>
4. Add the following lines to your `~/.ssh/config` file (replace <login> with
   your IoT-Lab login:
<pre>
Host iotlab
     Hostname saclay.iot-lab.info
     User <login>
Host node-a8-*
    User root
    ProxyCommand ssh iotlab -W %h:%p
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
</pre>
5. Launch the demo on nodes A8 140 (the border router) and A8 138, 139, 141 and
   142 (the demo nodes). We configure an experiment with 120m duration.
<pre>
$ cd utils/iotlab
$ ./iotlab-launch-demo.sh 120 140 '138 139 141 142'
</pre>
6. You should now see a new node popping up on the
   [RIOT Demo Dashboard](http://riot-demo.inria.fr). The A8_M3 node is also visible
   on the [FIT Live Camera](http://demo-fit.saclay.inria.fr).
