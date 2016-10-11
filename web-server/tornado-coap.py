
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

periodic_cb = None


@gen.coroutine
def _push_time():
    if len(GLOBALS['sockets']) != 0:
        protocol = yield from Context.create_client_context()
        request = Message(code=GET)
        request.set_request_uri('coap://localhost/time')
        try:
            response = yield from protocol.request(request).response
        except Exception as e:
            print('Failed to fetch resource: \n{0}'.format(e))
        else:
            result = ('Result: {}<br/>{}'
                      .format(response.code, response.payload.decode('ascii')))
            for socket in GLOBALS['sockets']:
                socket.write_message(result)
            # print(result.replace('<br/>', '\n'))


def _write_api(handler, link_header):
    link = link_header.decode('ascii').replace(' ', '')
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


class CoapAPIHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        protocol = yield from Context.create_client_context()
        request = Message(code=GET)
        request.set_request_uri('coap://localhost/.well-known/core')
        try:
            response = yield from protocol.request(request).response
        except Exception as e:
            self.write('Failed to fetch resource:<br/>')
            self.write(e)
        else:
            payload = "{}".format(response.payload)\
                .replace('<', '&lt;')\
                .replace('>', '&gt;')
            self.write('Result: {}<br/>{}<br/>'.format(response.code, payload))
            _write_api(self, response.payload)

        self.finish()


class CoapTimeHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        protocol = yield from Context.create_client_context()
        request = Message(code=GET)
        request.set_request_uri('coap://localhost/time')

        try:
            response = yield from protocol.request(request).response
        except Exception as e:
            self.write('Failed to fetch resource:<br/>')
            self.write(e)
        else:
            self.write('Result: {}<br/>{}'.format(response.code,
                                                  response.payload))
        self.finish()


class CoapBlockHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        protocol = yield from Context.create_client_context()
        request = Message(code=GET)
        request.set_request_uri('coap://localhost/other/block')

        try:
            response = yield from protocol.request(request).response
        except Exception as e:
            self.write('Failed to fetch resource:<br/>')
            self.write(e)
        else:
            self.write('Result: {}<br/>{}'.format(response.code,
                                                  response.payload))
        self.finish()

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        """Insert a message."""
        payload = self.get_argument('value').encode('ascii')
        context = yield from Context.create_client_context()

        # yield from asyncio.sleep(2)

        request = Message(code=PUT, payload=payload)
        request.opt.uri_host = '127.0.0.1'
        request.opt.uri_path = ("other", "block")

        response = yield from context.request(request).response

        self.write('Result: {}<br/>{}'.format(response.code,
                                              response.payload))


class CoapSeparateBlockHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        protocol = yield from Context.create_client_context()
        request = Message(code=GET)
        request.set_request_uri('coap://localhost/other/separate')
        try:
            response = yield from protocol.request(request).response
        except Exception as e:
            self.write('Failed to fetch resource:<br/>')
            self.write(e)
        else:
            self.write('Result: {}<br/>{}'.format(response.code,
                                                  response.payload))
        self.finish()


class MainHandler(web.RequestHandler):
    # @tornado.web.asynchronous
    def get(self, path=None):
        self.render("index.html", title="Getting CoAP with websockets")
        # self.finish()


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
    PeriodicCallback(_push_time, 50).start()

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
