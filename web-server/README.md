### Start tornado web server

python tornado-coap.py --http-port=8080 --hostname=fit-demo-dev

### Open a navigator

* [http://fit-demo-dev:8080] => open web socket and start receiving data from
  available nodes.
* [http://fit-demo-dev:8080/nodes] => list available nodes

### Post a value (indirect call to CoAP put)

```bash
curl -H "Content-Type: application/json" -X POST -d '{"node":"fd00:abad:1e:102:5846:257d:3b04:f9d6","path":"/led", "payload":"1"}' http://fit-demo-dev:8080
```
