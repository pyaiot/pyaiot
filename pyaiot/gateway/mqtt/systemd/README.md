## Mosquitto RSMB MQTT broker

To interact with constrained nodes using MQTT, we use the MQTT to MQTT-SN
gateway [Mosquitto.rsmb](https://github.com/eclipse/mosquitto.rsmb).

### Installation on a Raspberry Pi

* Clone the repository:
<pre>
    cd /opt && mkdir /opt/mqtt
    git clone https://github.com/eclipse/mosquitto.rsmb.git
</pre>

* Build the MQTT broker:
<pre>
    cd mosquitto.rsmb/
    make -C rsmb/src
</pre>

* Add the file `config.conf` in `/opt/mqtt/mosquitto.rsmb/` with the following
  content:
<pre>
# add some debug output
trace_output protocol
# listen for MQTT-SN traffic on UDP port 1885
listener 1885 INADDR_ANY mqtts
  ipv6 true
# listen to MQTT connections on tcp port 1886
listener 1886 INADDR_ANY
  ipv6 true
</pre>

* Then copy the [systemd service](mosquitto.rsmb.service) file to    `/lib/systemd/system`, enable and start the service
<pre>
    sudo cp mosquitto.rsmb.service /lib/systemd/system/.
    sudo systemctl enable mosquitto.rsmb.service
    sudo systemctl start mosquitto.rsmb.service
</pre>
