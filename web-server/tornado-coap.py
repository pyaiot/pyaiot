
import os
import sys
import socket
import time
import os.path
import tornado
import asyncio
import json
import logging
from errno import EWOULDBLOCK, EAGAIN
from tornado import gen, web, websocket
from tornado.ioloop import PeriodicCallback, IOLoop
from tornado.netutil import set_close_exec
from tornado.options import define, options
import tornado.platform.asyncio
from aiocoap import Context, Message, GET, PUT


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')

GLOBALS = {
    'time_sockets': [],
    'coap_nodes': {},
    'coap_sockets': [],
}


def _to_html(string):
    """Convert html special characters."""
    return string\
        .replace('<', '&lt;')\
        .replace('>', '&gt;')


def _endpoints(link_header):
    link = link_header.replace(' ', '')
    return link.split(',')


def _active_nodes():
    result = []
    current_time = int(time.time())
    for ip, dt in GLOBALS['coap_nodes'].items():
        if current_time < dt + options.max_time:
            result.append(ip)

    return result


@gen.coroutine
def _request_nodes():
    """Callback functions called after fetching new nodes."""
    if len(GLOBALS['coap_sockets']) == 0:
        return

    for node in _active_nodes():
        coap_node_url = 'coap://[{}]'.format(node)
        code, payload = yield _coap_resource('{0}/.well-known/core'
                                             .format(coap_node_url),
                                             method=GET)

        for ws in GLOBALS['coap_sockets']:
            ws.write_message('Node: <b>{}</b><br/>'
                             'Code: <b>{}</b><br/>'
                             'Payload: {}'
                             .format(node, code, _to_html(payload)))

        for endpoint in _endpoints(payload):
            elems = endpoint.split(';')
            path = elems.pop(0).replace('<', '').replace('>', '')
            if 'well-known/core' in path:
                continue

            code, payload = yield _coap_resource('{}{}'
                                                 .format(coap_node_url, path),
                                                 method=GET)
            for ws in GLOBALS['coap_sockets']:
                data = json.dumps({'endpoint': path, 'data': payload,
                                   'node': node})
                ws.write_message(data)


@gen.coroutine
def _coap_resource(url, method=GET, payload=b''):
    protocol = yield Context.create_client_context()
    request = Message(code=method, payload=payload)
    request.set_request_uri(url)
    try:
        response = yield protocol.request(request).response
    except Exception as e:
        code = "Failed to fetch resource"
        payload = '{}'.format(e)
    else:
        code = response.code
        payload = response.payload.decode('ascii')
    finally:
        yield protocol.shutdown()

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
    if len(GLOBALS['time_sockets']) != 0:
        code, payload = yield _coap_resource('coap://localhost/time')
        for ws in GLOBALS['time_sockets']:
            ws.write_message('Code: <b>{}</b><br/>Payload: {}'.format(code,
                                                                      payload))


class CoapAPIHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        code, payload = yield _coap_resource('coap://localhost/'
                                             '.well-known/core')
        self.write(payload.replace('<', '&lt;').replace('>', '&gt;') + '<br/>')
        _write_api(self, payload)
        self.finish()


class CoapTimeHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        code, payload = yield _coap_resource('coap://localhost/time')
        self.render("time.html", title="Time", time=payload)


class CoapContentHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        code, payload = yield _coap_resource('coap://localhost/content')
        self.render("content.html", title="Content text form", content=payload)

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        """Insert a message."""
        block = self.get_body_argument("content")
        code, payload = yield _coap_resource('coap://localhost/content',
                                             method=PUT,
                                             payload=block.encode('ascii'))
        self.redirect('/content')


class CoapVersionHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        code, payload = yield _coap_resource('coap://localhost/version')
        self.render("version.html", title="Python version", version=payload)


class CoapKernelHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        code, payload = yield _coap_resource('coap://localhost/kernel')
        self.render("kernel.html", title="Kernel version", kernel=payload)


class DashboardHandler(web.RequestHandler):
    # @tornado.web.asynchronous
    def get(self, path=None):
        self.render("dashboard.html", title="CoAP nodes dashboard")


class MainHandler(web.RequestHandler):
    # @tornado.web.asynchronous
    def get(self, path=None):
        self.render("index.html", title="Getting CoAP with websockets")


class TimeWebSocket(websocket.WebSocketHandler):
    def open(self):
        GLOBALS['time_sockets'].append(self)
        print("Time WebSocket opened")

    def on_close(self):
        print("Time WebSocket closed")
        GLOBALS['time_sockets'].remove(self)


class CoapWebSocket(websocket.WebSocketHandler):
    def open(self):
        GLOBALS['coap_sockets'].append(self)
        print("Coap WebSocket opened")

    def on_close(self):
        print("Coap WebSocket closed")
        GLOBALS['coap_sockets'].remove(self)


class NodesUDPListener(object):
    """UDP listener class."""

    def __init__(self, name, port, on_receive, address=None,
                 family=socket.AF_INET6, io_loop=None):
        """Constructor."""
        self.io_loop = io_loop or IOLoop.instance()
        self._on_receive = on_receive
        self._log = logging.getLogger(name)
        self._sockets = []

        flags = socket.AI_PASSIVE

        if hasattr(socket, "AI_ADDRCONFIG"):
            flags |= socket.AI_ADDRCONFIG

        # find all addresses to bind, bind and register the "READ" callback
        for res in set(socket.getaddrinfo(address, port,
                                          family,
                                          socket.SOCK_DGRAM, 0, flags)):
            af, sock_type, proto, canon_name, sock_addr = res
            self._open_and_register(af, sock_type, proto, sock_addr)

        self._log.info('Nodes listener started, listening on port {0}'
                       .format(sock_addr[1]))

    def _open_and_register(self, af, sock_type, proto, sock_addr):
        sock = socket.socket(af, sock_type, proto)
        set_close_exec(sock.fileno())
        if os.name != 'nt':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        sock.bind(sock_addr)

        def read_handler(fd, events):
            while True:
                try:
                    data, address = sock.recvfrom(65536)
                except socket.error as e:
                    if e.args[0] in (EWOULDBLOCK, EAGAIN):
                        return
                    raise
                self._on_receive(data, address)
                self._log.info('Received "{0}" message from node "{1}"'
                               .format(data.decode().strip(), address[0]))

        self.io_loop.add_handler(sock.fileno(), read_handler, IOLoop.READ)
        self._sockets.append(sock)

    def stop(self):
        """Stop the UDP server."""
        self._log.debug('Closing %d socket(s)...', len(self._sockets))
        for sock in self._sockets:
            self.io_loop.remove_handler(sock.fileno())
            sock.close()


class RiotBrokerApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self):
        self._nodes = {}
        self._log = logging.getLogger("riot broker")
        handlers = [
            (r'/', MainHandler),
            (r'/time', CoapTimeHandler),
            (r'/content', CoapContentHandler),
            (r'/version', CoapVersionHandler),
            (r'/kernel', CoapKernelHandler),
            (r'/dashboard', DashboardHandler),
            (r'/api', CoapAPIHandler),
            (r"/time_ws", TimeWebSocket),
            (r"/coap_ws", CoapWebSocket),
        ]
        settings = {'debug': True,
                    "cookie_secret": "MY_COOKIE_ID",
                    "xsrf_cookies": True,
                    'static_path': os.path.join(os.path.dirname(__file__),
                                                "static"),
                    'template_path': os.path.join(os.path.dirname(__file__),
                                                  "static")
                    }
        super().__init__(handlers, **settings)
        self.listener = NodesUDPListener('node listener',
                                         options.listener_port,
                                         on_receive=self.on_receive_packet)
        self._log.info('Application started, listening on port {0}'
                       .format(options.http_port))

    def on_receive_packet(self, data, address):
        """Callback triggered when an alive packet is received."""
        GLOBALS['coap_nodes'].update({address[0]: int(time.time())})


def parse_command_line():
    """Parse command line arguments for Riot broker application."""
    define("listener_port", default=8888, help="Node listener UDP port.")
    define("http_port", default=8080, help="Web application HTTP port")
    define("max_time", default=120, help="Retention time for lost nodes.")
    options.parse_command_line()


if __name__ == '__main__':
    parse_command_line()
    try:
        ioloop = asyncio.get_event_loop()
        tornado.platform.asyncio.AsyncIOMainLoop().install()
        PeriodicCallback(_push_time, 100).start()
        PeriodicCallback(_request_nodes, 2000).start()

        app = RiotBrokerApplication()
        app.listen(options.http_port)
        ioloop.run_forever()
    except KeyboardInterrupt:
        print("Exiting")
        app.listener.stop()
        ioloop.stop()
        sys.exit()
