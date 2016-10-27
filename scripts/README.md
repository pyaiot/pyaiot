## Demos scripts

Here one can find scripts to automatize the deployment of demonstrations. This
README explains how to previously setup your environment and how to run the
script.

### IoT-LAB A8-M3 demo

This demonstration is provided by `iotlab-launch-demo` and will book 2 nodes in
the IoT-LAB testbed in Saclay site. One of the node is configured as a boarder
router, the other one is running the demonstration firmware `node_iotlab_a8_m3`.

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
4. Launch the demo on nodes A8 144 (the border router) and A8 145 (the demo
   node).
<pre>
$ cd demos/scripts
$ ./iotlab-launch-demo.sh 144 ./gnrc_border_router.elf 145 ./dashboard_riot_a8_m3.elf
</pre>
5. You should now see the demo node on the [fit-demo live
   camera](demo-fit.saclay.inria.fr) and play its LED from the [RIOT
   dashboard](fit-demo.saclay.inria.fr/dashboard)

