"""Server helper functions module."""

import logging
import signal
from functools import partial
import tornado


def signal_handler(server, app_close, sig, frame):
    """Triggered when a signal is received from system."""
    _ioloop = tornado.ioloop.IOLoop.instance()

    def shutdown():
        """Force server and ioloop shutdown."""
        logging.info('Shuting down server')
        tornado.platform.asyncio.AsyncIOMainLoop().stop()
        if app_close is not None:
            app_close()
        if server is not None:
            server.stop()
        _ioloop.stop()

    logging.warning('Caught signal: %s', sig)
    _ioloop.add_callback_from_signal(shutdown)


def start_application(app, port=None, close_client=False):
    """Start a tornado application."""
    _ioloop = tornado.ioloop.IOLoop.current()
    _server = None
    if port is not None:
        _server = app.listen(port)

    if not close_client:
        app.close_client = None

    signal.signal(signal.SIGTERM,
                  partial(signal_handler, _server, app.close_client))
    signal.signal(signal.SIGINT,
                  partial(signal_handler, _server, app.close_client))

    _ioloop.start()
