## Install the tornado eb server

### Prequisities

Install javascript and css required packages with [bower](https://bower.io/).

1. Install Bower
```shell
$ sudo npm install bower -g
```
2. Install the web packages:
```
$ cd web-server/static
$ bower install
```

### Start tornado web server

python3 web-server/tornado-coap.py --http-port=8080 --websocket-host=fit-demo-dev --websocket-port=8080

### Open a navigator

* [http://fit-demo-dev:8080] => open web socket and start receiving data from
  available nodes.
* [http://fit-demo-dev:8080/nodes] => list available nodes

### Post a value (indirect call to CoAP put)

```bash
curl -H "Content-Type: application/json" -X POST -d '{"node":"fd00:abad:1e:102:5846:257d:3b04:f9d6","path":"/led", "payload":"1"}' http://fit-demo-dev:8080
```
