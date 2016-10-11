### Start tornado web server

python tornado-coap.py

### Open a navigator

* [http://localhost:8888] => open web socket on CoAP `time` resource
* [http://localhost:8888/block] => get `other/block` resource

### Post a value (indirect call to CoAP put)

```bash
curl --data "value=new value again" http://localhost:8888/block
```
