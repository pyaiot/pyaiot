#!/bin/bash

BR_A8_ID=$1
BR_FW=$2

DEMO_A8_ID=$3
DEMO_FW=$4

EXP_DURATION=$5

ETHOS_DIR="~/A8/riot/RIOT/dist/tools/ethos"
SSH_MAX_TRIES=30

[ -z "${BR_A8_ID}" -o -z "${BR_FW}" -o -z "${DEMO_A8_ID}" -o -z "${DEMO_FW}" -o -z "${EXP_DURATION}" ] && {
     echo "usage: $0 <br_node_id> <br_node_firmware> <demo_node_id> <demo_node_firmware> <experiment_duration>"
     exit 1
}

start_experiment() {
    # Submit an experiment in Saclay on nodes A8 144 and 145
    # - node-a8-144 will be used as a border router
    # - node-a8-145 will run the dashboard enable firmware. This node is visible at
    # http://demo-fit.saclay.inria.fr
    echo "Starting new experiment"
    experiment-cli submit -d ${EXP_DURATION} -l saclay,a8,${BR_A8_ID}+${DEMO_A8_ID}
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
            experiment-cli stop
            echo "Could not connect to one of the nodes, exiting"
            exit 1
        fi
    done
}

start_border_router() {
    # Flash the firmwares on the nodes using ssh-cli-tools
    # 1. Flash the border router
    echo "Flashing border router firmware"
    open-a8-cli update-m3 ${BR_FW} -l saclay,a8,${BR_A8_ID} > iotlab-launch-demo.log 2>&1

    echo "Configuring the border router"
    # Configure RIOT on the border router
    ssh node-a8-${BR_A8_ID} "cd ${ETHOS_DIR}/../uhcpd && make clean all" > /dev/null 2>&1
    ssh node-a8-${BR_A8_ID} "cd ${ETHOS_DIR} && make clean all" > /dev/null 2>&1

    # Stop any running screen
    ssh node-a8-${BR_A8_ID} "screen -X -S br quit" > /dev/null 2>&1

    # Start the border router
    PREFIX_LINE=`ssh node-a8-144 "source /etc/profile.d/ipv6 && printenv | grep INET6_PREFIX= 2>/dev/null"`
    PREFIX_LIST=(${PREFIX_LINE/\=/ })
    PREFIX=${PREFIX_LIST[${#PREFIX_LIST[@]} - 1]}::/64
    ssh node-a8-${BR_A8_ID} "screen -S br -dm bash -c \"cd ${ETHOS_DIR} && \
        ./start_network.sh /dev/ttyA8_M3 tap0 ${PREFIX}\"" >> iotlab-launch-demo.log 2>&1
    sleep 10s
    echo "Border router started"
}

start_demo_node() {
    # 2. Flash the demo node
    echo "Flashing Demo firmware"
    open-a8-cli update-m3 ${DEMO_FW} -l saclay,a8,${DEMO_A8_ID} >> iotlab-launch-demo.log 2>&1
}

stop_demo() {
    echo "Exiting"
    trap "" INT QUIT TERM EXIT
    exit 1
}

trap "stop_demo" INT QUIT TERM EXIT

start_experiment && check_ssh_available && start_border_router && start_demo_node
