
import os
import sys
import time
import os.path
import tornado
import asyncio
import json
import logging
from tornado import gen, web, websocket
from tornado.ioloop import PeriodicCallback
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
    internal_logger.debug("Broadcasting message '{}' to web clients."
                          .format(message))
    for ws in GLOBALS['coap_sockets']:
        ws.write_message(message)


def _refresh_node(remote):
    """Refresh node last check or add it to the list of active nodes."""
    node = CoapNode(remote)
    node.check_time = time.time()
    if node not in GLOBALS['coap_nodes']:
        _broadcast_message(json.dumps({'command': 'new',
                                       'node': node.address}))
        GLOBALS['coap_nodes'].append(node)
        _discover_node(node)
    else:
        index = GLOBALS['coap_nodes'].index(node)
        GLOBALS['coap_nodes'][index].check_time = time.time()


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
            internal_logger.debug("Removing inactive node {}"
                                  .format(node.address))
            _broadcast_message(json.dumps({'node': node.address,
                                           'command': 'out'}))
    GLOBALS['coap_nodes'] = nodes


@gen.coroutine
def _discover_node(node, ws=None):
    """Callback functions called after fetching new nodes."""
    coap_node_url = 'coap://[{}]'.format(node.address)
    if len(node.endpoints) == 0:
        internal_logger.debug("Discovering node {}".format(node.address))
        code, payload = yield _coap_resource('{0}/.well-known/core'
                                             .format(coap_node_url),
                                             method=GET)
        node.endpoints = _endpoints(payload)

    messages = {}
    endpoints = [endpoint
                 for endpoint in node.endpoints
                 if 'well-known/core' not in endpoint]
    for endpoint in endpoints:
        elems = endpoint.split(';')
        path = elems.pop(0).replace('<', '').replace('>', '')

        code, payload = yield _coap_resource('{0}{1}'
                                             .format(coap_node_url, path),
                                             method=GET)
        messages[endpoint] = json.dumps({'endpoint': path,
                                         'data': payload,
                                         'node': node.address,
                                         'command': 'update'})

    for endpoint in endpoints:
        message = messages[endpoint]
        if ws is None:
            _broadcast_message(messages)
        else:
            try:
                ws.write_message(message)
            except websocket.WebSocketClosedError:
                internal_logger.debug("Cannot write on a closed websocket.")


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
        payload = response.payload.decode('utf-8')
    finally:
        yield from protocol.shutdown()

    internal_logger.debug('Code: {0} - Payload: {1}'.format(code, payload))

    return code, payload


class CoapNode(object):
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


class CoapAliveResource(resource.Resource):
    """CoAP server running within the tornado application."""

    def __init__(self):
        super(CoapAliveResource, self).__init__()

    @asyncio.coroutine
    def render_post(self, request):
        payload = request.payload.decode('utf8')
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]
        internal_logger.debug("CoAP Alive POST received from {}"
                              .format(remote))

        _refresh_node(remote)

        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))


class CoapServerResource(resource.Resource):
    """CoAP server running within the tornado application."""

    def __init__(self):
        super(CoapServerResource, self).__init__()

    @asyncio.coroutine
    def render_post(self, request):
        payload = request.payload.decode('utf-8')
        try:
            remote = request.remote[0]
        except TypeError:
            remote = request.remote.sockaddr[0]
        internal_logger.debug("CoAP POST received from {} with payload: {}"
                              .format(remote, payload))

        if CoapNode(remote) in GLOBALS['coap_nodes']:
            path, data = payload.split(":", 1)
            _broadcast_message(json.dumps({'endpoint': '/' + path,
                                           'data': data,
                                           'node': remote,
                                           'command': 'update'}))
        return Message(code=CHANGED,
                       payload="Received '{}'".format(payload).encode('utf-8'))


class ActiveNodesHandler(web.RequestHandler):
    @tornado.web.asynchronous
    @gen.coroutine
    def get(self):
        nodes = []
        for node in GLOBALS['coap_nodes']:
            try:
                nodes.append(json.dumps(node))
            except:
                pass
        self.write({'nodes': json.dumps(nodes)})
        self.finish()


class DashboardHandler(web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, path=None):
        self.render("dashboard.html",
                    wsserver="{}:{}".format(options.websocket_host,
                                            options.websocket_port),
                    title="RIOT Dashboard")

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        """Forward POST request to a CoAP PUT request."""
        data = json.loads(self.request.body.decode('utf-8'))
        node = data['node']
        path = data['path']
        payload = data['payload']
        internal_logger.debug("Translate POST request ('{}') received to CoAP"
                              "PUT request".format(data))

        if CoapNode(node) not in GLOBALS['coap_nodes']:
            return
        code, payload = yield _coap_resource('coap://[{0}]{1}'
                                             .format(node, path),
                                             method=PUT,
                                             payload=payload.encode('ascii'))


class DashboardWebSocket(websocket.WebSocketHandler):
    def open(self):
        self.set_nodelay(True)
        internal_logger.debug("New websocket opened")
        GLOBALS['coap_sockets'].append(self)
        for node in GLOBALS['coap_nodes']:
            self.write_message(json.dumps({'command': 'new',
                                           'node': node.address}))
            _discover_node(node, self)

    def on_close(self):
        internal_logger.debug("Websocket closed")
        if self in GLOBALS['coap_sockets']:
            GLOBALS['coap_sockets'].remove(self)


class RiotDashboardApplication(web.Application):
    """Tornado based web application providing live nodes on a network."""

    def __init__(self):
        self._nodes = {}
        self._log = logging.getLogger("riot broker")
        if options.debug:
            self._log.setLevel(logging.DEBUG)

        handlers = [
            (r'/', DashboardHandler),
            (r"/ws", DashboardWebSocket),
            (r'/nodes', ActiveNodesHandler),
        ]
        settings = {'debug': True,
                    "cookie_secret": "MY_COOKIE_ID",
                    "xsrf_cookies": False,
                    'static_path': os.path.join(os.path.dirname(__file__),
                                                "static"),
                    'template_path': os.path.join(os.path.dirname(__file__),
                                                  "static")
                    }
        super().__init__(handlers, **settings)
        self._log.info('Application started, listening on port {0}'
                       .format(options.http_port))


def parse_command_line():
    """Parse command line arguments for Riot broker application."""
    define("http_port", default=8080,
           help="Web application HTTP port")
    define("websocket_port", default=8080,
           help="Web application websocket port")
    define("websocket_host", default="localhost",
           help="Public websocket server hostname")
    define("max_time", default=120,
           help="Retention time for lost nodes (s).")
    define("debug", default=False,
           help="Enable debug mode.")
    options.parse_command_line()

    if options.debug:
        internal_logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    parse_command_line()
    try:
        # Tornado ioloop initialization
        ioloop = asyncio.get_event_loop()
        tornado.platform.asyncio.AsyncIOMainLoop().install()
        PeriodicCallback(_check_dead_nodes, 1000).start()

        # Aiocoap server initialization
        root_coap = resource.Site()
        root_coap.add_resource(('server', ), CoapServerResource())
        root_coap.add_resource(('alive', ), CoapAliveResource())
        asyncio.async(Context.create_server_context(root_coap))

        # Start tornado application
        app = RiotDashboardApplication()
        app.listen(options.http_port)
        ioloop.run_forever()
    except KeyboardInterrupt:
        print("Exiting")
        ioloop.stop()
        sys.exit()
