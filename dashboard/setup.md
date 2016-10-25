# Setup instructions for running riot dashboard demo on raspberry pi

## install Node.js

    ssh pi@fit-demo-dev

install node package for ARM

    wget http://node-arm.herokuapp.com/node_latest_armhf.deb 
    sudo dpkg -i node_latest_armhf.deb

    $ node -v
    v4.2.1

update node

    sudo npm cache clean -f
    sudo npm install -g n
    sudo n stable

    $ node -v
    v6.2.1

## install freeboard.io

    cd demo

clone freeboard repo

    git clone https://github.com/Freeboard/freeboard.git
    cd freeboard
    npm install

install grunt cli

    npm install -g grunt-cli

    grunt

## serve 