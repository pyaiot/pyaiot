
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
import aiocoap.resource as resource
from aiocoap import Context, Message, GET, PUT, CHANGED


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')
internal_logger = logging.getLogger("tornado.internal")

GLOBALS = {
    'coap_nodes': [],
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


def _broadcast_message(message):
    """Broadcast message on all opened websockets."""
    for ws in GLOBALS['coap_sockets']:
        ws.write_message(message)


@gen.coroutine
def _check_dead_nodes():
    """Find dead nodes in the list of known nodes and remove them."""
    if len(GLOBALS['coap_nodes']) == 0:
        return

    nodes = []
    for node in GLOBALS['coap_nodes']:
        if node.active():
            nodes += [node]
        else:
            _broadcast_message(json.dumps({'node': node.address,
                                           'command': 'out'}))
    GLOBALS['coap_nodes'] = nodes


@gen.coroutine
def _request_nodes():
    """Callback functions called after fetching new nodes."""
    if len(GLOBALS['coap_sockets']) == 0:
        return

    for node in GLOBALS['coap_nodes']:
        coap_node_url = 'coap://[{}]'.format(node.address)
        if len(node.endpoints) == 0:
            code, payload = yield _coap_resource('{0}/.well-known/core'
                                                 .format(coap_node_url),
                                                 method=GET)
            node.endpoints = _endpoints(payload)

        for endpoint in node.endpoints:
            elems = endpoint.split(';')
            path = elems.pop(0).replace('<', '').replace('>', '')
            if 'well-known/core' in path:
                continue

            code, payload = yield _coap_resource('{0}{1}'
                                                 .format(coap_node_url, path),
                                                 method=GET)
            _broadcast_message(json.dumps({'endpoint': path,
                                           'data': payload,
                                           'node': node.address,
                                           'command': 'update'}))


@gen.coroutine
def _coap_resource(url, method=GET, payload=b''):
    protocol = yield from Context.create_client_context()
    request = Message(code=method, payload=payload)
    request.set_request_uri(url)
    try:
        response = yield from protocol.request(request).response
    except Exception as e:
        code = "Failed to fetch resource"
        payload = '{0}'.format(e)
    else:
        code = response.code
        payload = response.payload.decode('ascii')
    finally:
        yield from protocol.shutdown()

    internal_logger.info('Code: {0} - Payload: {1}'.format(code, payload))

    return code, payload


class CoAPNode(object):
    """Object defining a CoAP node."""

    def __init__(self, address, check_time=time.time(), endpoints=[]):
        self.address = address
        self.check_time = check_time
        self.endpoints = endpoints

    def __eq__(self, other):
        return self.address == other.address

    def __neq__(self, other):
        return self.address != other.address

    def __repr__(self):
        return("Node '{}', Last check: {}, Endpoints: {}"
               .format(self.address, self.check_time, self.endpoints))

    def active(self):
        """check if the node is still active and responding."""
        return int(time.time()) < self.check_time + options.max_time


class CoAPServerResource(resource.Resource):
    """CoAP server running withni the tornado application"""

    def __init__(self):
        super(CoAPServerResource, self).__init__()

    @asyncio.coroutine
    def render_post(self, request):
        payload = request.payload.decode('utf8')
        internal_logger.info("CoAP PORT received from {} with payload: {}"
                             .format(request.remote.sockaddr[0], payload))

        path, data = payload.split(":")
        _broadcast_message(json.dumps({'endpoint': path,
                                       'data': data,
                                       'node': request.remote.sockaddr[0],
                                       'command': 'update'}))
        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))


class ActiveNodesHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        self.write({'nodes': list([node.address
                                   for node in GLOBALS['coap_nodes']])})
        self.finish()


class CoapPostHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        pass

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        """Forward a CoAP put."""
        data = json.loads(self.request.body)
        node = data['node']
        path = data['path']
        payload = data['payload']
        code, payload = yield _coap_resource('coap://[{0}]{1}'
                                             .format(node, path),
                                             method=PUT,
                                             payload=payload.encode('ascii'))


class DashboardHandler(web.RequestHandler):
    # @tornado.web.asynchronous
    def get(self, path=None):
        self.render("dashboard.html",
                    server="localhost",
                    port=options.http_port,
                    title="CoAP nodes dashboard")


class CoapWebSocket(websocket.WebSocketHandler):
    def open(self):
        GLOBALS['coap_sockets'].append(self)
        for node in GLOBALS['coap_nodes']:
            _broadcast_message(json.dumps({'command': 'new',
                                           'node': node.address}))

    def on_close(self):
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


class RiotDashboardApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self):
        self._nodes = {}
        self._log = logging.getLogger("riot broker")
        handlers = [
            (r'/', DashboardHandler),
            (r'/post', CoapPostHandler),
            (r'/nodes', ActiveNodesHandler),
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
        node = CoAPNode(address[0])
        if node not in GLOBALS['coap_nodes']:
            _broadcast_message(json.dumps({'command': 'new',
                                           'node': node.address}))
            GLOBALS['coap_nodes'].append(node)
        else:
            index = GLOBALS['coap_nodes'].index(node)
            GLOBALS['coap_nodes'][index].check_time = time.time()


def parse_command_line():
    """Parse command line arguments for Riot broker application."""
    define("listener_port", default=8888, help="Node listener UDP port.")
    define("http_port", default=8080, help="Web application HTTP port")
    define("max_time", default=120, help="Retention time for lost nodes (s).")
    define("delay_refresh", default=200,
           help="Delay between nodes refresh (ms).")
    options.parse_command_line()


if __name__ == '__main__':
    parse_command_line()
    try:
        ioloop = asyncio.get_event_loop()
        tornado.platform.asyncio.AsyncIOMainLoop().install()
        PeriodicCallback(_request_nodes, options.delay_refresh).start()
        PeriodicCallback(_check_dead_nodes, 100).start()
        root_coap = resource.Site()
        root_coap.add_resource(('server', ), CoAPServerResource())
        asyncio.async(Context.create_server_context(root_coap))

        app = RiotDashboardApplication()
        app.listen(options.http_port)
        ioloop.run_forever()
    except KeyboardInterrupt:
        print("Exiting")
        app.listener.stop()
        ioloop.stop()
        sys.exit()
