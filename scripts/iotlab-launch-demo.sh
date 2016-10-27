#!/bin/bash

BR_FW = $1
DEMO_FW = $2

# Submit an experiment in Saclay on nodes A8 144 and 145
# - node-a8-144 will be used as a border router
# - node-a8-145 will run the dashboard enable firmware. This node is visible at
# http://demo-fit.saclay.inria.fr
experiment-cli submit -d 120 -l saclay,a8,144+145
experiment-cli wait

# Flash the firmwares on the nodes using ssh-cli-tools
# 1. Flash the border router
open-a8-cli update-m3 $(BR_FW) -l saclay,a8,144

# Start the border router
ssh -t node-a8-144 'cd ~/A8/riot/RIOT/dist/tools/ethos&& screen -S br ./start_network.sh /dev/ttyA8_M3 tap0 2001:0660:3207:490::/64'

# 2. Flash the demo node
open-a8-cli update-m3 $(DEMO_FW) -l saclay,a8,145


