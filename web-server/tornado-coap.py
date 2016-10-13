
import os.path
import tornado
import asyncio
from tornado import gen, web, websocket
from tornado.ioloop import PeriodicCallback
import tornado.platform.asyncio
from aiocoap import Context, Message, GET, PUT

GLOBALS = {
    'sockets': []
}


def _coap_resource(url, method=GET, payload=b''):
    protocol = yield from Context.create_client_context()
    request = Message(code=method, payload=payload)
    request.set_request_uri(url)
    try:
        response = yield from protocol.request(request).response
    except Exception as e:
        code = "Failed to fetch resource"
        payload = '{}'.format(e)
    else:
        code = response.code
        payload = response.payload.decode('ascii')
    finally:
        yield from protocol.shutdown()

    print('Code: {} - Payload: {}'.format(code, payload))

    return code, payload


def _write_api(handler, link_header):
    link = link_header.replace(' ', '')
    endpoints = link.split(',')
    for endpoint in endpoints:
        elems = endpoint.split(';')
        path = elems.pop(0).replace('<', '').replace('>', '')
        handler.write("<b>Path:</b> {}<br/>".format(path))
        sm = "<i>Supported methods:</i> "
        vt = "<i>Value type:</i> "
        em = "<i>Extra options:</i> "
        ms = "<i>Maximum size:</i> "
        for e in elems:
            if e.startswith('if='):
                sm += ", ".join(e.split('=')[1].split('/'))
            elif e.startswith('ct='):
                ms += str(e)
            elif e.startswith('rt='):
                vt += e.split('=')[1]
            else:
                em += e + " "
        handler.write("&nbsp;&nbsp;{}<br/>".format(sm))
        handler.write("&nbsp;&nbsp;{}<br/>".format(vt))
        handler.write("&nbsp;&nbsp;{}<br/>".format(em))
        handler.write("&nbsp;&nbsp;{}<br/>".format(ms))


@gen.coroutine
def _push_time():
    if len(GLOBALS['sockets']) != 0:
        code, payload = yield from _coap_resource('coap://localhost/time',
                                                  method=GET)
        for socket in GLOBALS['sockets']:
            socket.write_message('Code: <b>{}</b><br/>Payload: {}'
                                 .format(code, payload))


class CoapAPIHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        code, payload = yield from _coap_resource('coap://localhost/'
                                                  '.well-known/core',
                                                  method=GET)
        self.write(payload.replace('<', '&lt;').replace('>', '&gt;') + '<br/>')
        _write_api(self, payload)
        self.finish()


class CoapTimeHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        code, payload = yield from _coap_resource('coap://localhost/time',
                                                  method=GET)
        self.write('Code: <b>{}</b><br/>{}'.format(str(code), payload))
        self.finish()


class CoapBlockHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        code, payload = yield from _coap_resource('coap://localhost/'
                                                  'other/block',
                                                  method=GET)
        self.render("block.html", title="Block text form", block=payload)

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        """Insert a message."""
        block = self.get_body_argument("block")
        code, payload = yield from \
            _coap_resource('coap://localhost/other/block',
                           method=PUT, payload=block.encode('ascii'))
        self.redirect('/block')


class CoapSeparateBlockHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        code, payload = yield from _coap_resource('coap://localhost/'
                                                  'other/separate',
                                                  method=GET)
        self.write('Separate:<br/>' + payload)
        self.finish()


class MainHandler(web.RequestHandler):
    # @tornado.web.asynchronous
    def get(self, path=None):
        self.render("index.html", title="Getting CoAP with websockets")


class ClientWebSocket(websocket.WebSocketHandler):
    def open(self):
        GLOBALS['sockets'].append(self)
        print("WebSocket opened")

    def on_close(self):
        print("WebSocket closed")
        GLOBALS['sockets'].remove(self)


if __name__ == '__main__':
    ioloop = asyncio.get_event_loop()
    tornado.platform.asyncio.AsyncIOMainLoop().install()
    PeriodicCallback(_push_time, 100).start()

    settings = {'debug': True,
                "cookie_secret": "MY_COOKIE_ID",
                # "xsrf_cookies": True,
                'static_path': os.path.join(os.path.dirname(__file__),
                                            "static"),
                'template_path': os.path.join(os.path.dirname(__file__),
                                              "static")
                }

    application = web.Application(
        [
            (r'/', MainHandler),
            (r'/time', CoapTimeHandler),
            (r'/block', CoapBlockHandler),
            (r'/separate', CoapSeparateBlockHandler),
            (r'/api', CoapAPIHandler),
            (r"/ws", ClientWebSocket),
        ],
        **settings,
    )
    print('Listening on http://localhost:8888')
    application.listen(8888)
    ioloop.run_forever()
