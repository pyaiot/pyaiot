#!/bin/bash

BR_A8_ID=$1
BR_FW=$2

DEMO_A8_ID=$3
DEMO_FW=$4

ETHOS_DIR="~/A8/riot/RIOT/dist/tools/ethos"
SSH_MAX_TRIES=30

start_experiment() {
    # Submit an experiment in Saclay on nodes A8 144 and 145
    # - node-a8-144 will be used as a border router
    # - node-a8-145 will run the dashboard enable firmware. This node is visible at
    # http://demo-fit.saclay.inria.fr
    echo "Starting new experiment"
    experiment-cli submit -d 120 -l saclay,a8,${BR_A8_ID}+${DEMO_A8_ID}
    experiment-cli wait
    echo "Experiment started"
}

check_ssh_available() {
    for node_id in ${BR_A8_ID} ${DEMO_A8_ID}
    do
        zero=0
        cpt=${SSH_MAX_TRIES}
        while ((cpt))
        do
            echo -ne "\e[0K\rNode ${node_id}: ${cpt} remaining ssh tries   "
            ssh -q node-a8-${node_id} exit > /dev/null 2>&1
            if [[ $? -eq $zero ]]
            then
                echo -e
                echo "SSH available on node-a8-${node_id}"
                break
            fi
            ((cpt--))
            sleep 2s
        done
        if [[ $cpt -eq $zero ]]
        then
            echo -e
            echo "Could not connect to one of the nodes, exiting"
            exit 1
        fi
    done
}

start_border_router() {
    # Flash the firmwares on the nodes using ssh-cli-tools
    # 1. Flash the border router
    echo "Flashing border router firmware"
    open-a8-cli update-m3 ${BR_FW} -l saclay,a8,${BR_A8_ID} > iotlab-launch-demo.log

    echo "Configuring the border router"
    # Configure RIOT on the border router
    ssh node-a8-${BR_A8_ID} "cd ${ETHOS_DIR}/../uhcpd && make clean all" > /dev/null
    ssh node-a8-${BR_A8_ID} "cd ${ETHOS_DIR} && make clean all" > /dev/null

    # Stop any running screen
    screen -X -S br quit

    # Start the border router
    PREFIX_LINE=`ssh node-a8-144 "source /etc/profile.d/ipv6 && printenv | grep INET6_PREFIX="`
    PREFIX_LIST=(${PREFIX_LINE/\=/ })
    PREFIX=${PREFIX_LIST[${#PREFIX_LIST[@]} - 1]}::/64
    screen -S br -dm ssh -t node-a8-${BR_A8_ID} "cd ${ETHOS_DIR} && ./start_network.sh /dev/ttyA8_M3 tap0 ${PREFIX}"
    echo "Border router started"
}

start_demo_node() {
    # 2. Flash the demo node
    open-a8-cli update-m3 ${DEMO_FW} -l saclay,a8,${DEMO_A8_ID} >> iotlab-launch-demo.log
}

stop_demo() {
    echo "Exiting"
    trap "" INT QUIT TERM EXIT
    exit 1
}

trap "stop_demo" INT QUIT TERM EXIT

start_experiment && check_ssh_available && start_border_router && start_demo_node
