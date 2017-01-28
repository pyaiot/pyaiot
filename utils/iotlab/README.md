## IoTLAB demo script

Here is a script that automatizes the deployment of demonstration nodes on
IoT-LAB. This README explains how to setup your environment and how to run
the script.

The `iotlab-launch-demo` script will book 2 nodes in the IoT-LAB testbed in
Saclay site. One of the node is configured as a border router, the other one
is running the demonstration firmware `node_iotlab_a8_m3`.

You need an IoT-LAB account to run this script.

#### Requirements

1. Install IoT-LAB cli-tools and ssh-cli-tools packages (you have to be part of
   the IoT-LAB organisation to access the later one, which is private for the
   moment):
<pre>
$ git clone git@github.com:iot-lab/ssh-cli-tools.git
$ cd ssh-cli-tools
$ pip install -e . --user
$ cd ..
$ git clone git@github.com:iot-lab/cli-tools.git
$ cd cli-tools
$ pip install -e . --user
$ cd ..
</pre>
2. Play at least once the [RIOT border router tutorial on IoT-LAB
   portal](https://www.iot-lab.info/tutorials/riot-public-ipv66lowpan-network-with-a8-m3-nodes/)
   Important: use the same directories on the Saclay site ssh frontend
3. Clone this repository:
<pre>
$ git clone git@gitlab.inria.fr:fit-saclay/demos.git
</pre>
4. Launch the demo on nodes A8 141 (the border router) and A8 142 (the demo
   node). We configure an experiment with 120m duration.
<pre>
$ cd utils/iotlab 
$ ./iotlab-launch-demo.sh 141 ./gnrc_border_router.elf 142 ./dashboard_riot_a8_m3.elf 120
</pre>
5. You should now see a new node popping up on the
   [RIOT Demo Dashboard](http://riot-demo.inria.fr). The A8_M3 node is also visible
   on the [FIT Live Camera](http://demo-fit.saclay.inria.fr).
