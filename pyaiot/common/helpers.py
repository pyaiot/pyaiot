"""Server helper functions module."""

import logging
import signal
from functools import partial
import tornado
from tornado.options import define, options

from pyaiot.common.auth import DEFAULT_KEY_FILENAME

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')

logger = logging.getLogger("pyaiot.helpers")


def parse_command_line(extra_args_func=None):
    """Parse command line arguments for any Pyaiot application."""
    if not hasattr(options, "config"):
        define("config", default=None, help="Config file")
    if not hasattr(options, "broker_host"):
        define("broker_host", default="localhost", help="Broker host")
    if not hasattr(options, "broker_port"):
        define("broker_port", default=8000, help="Broker websocket port")
    if not hasattr(options, "debug"):
        define("debug", default=False, help="Enable debug mode.")
    if not hasattr(options, "key_file"):
        define("key_file", default=DEFAULT_KEY_FILENAME,
               help="Secret and private keys filename.")
    if extra_args_func is not None:
        extra_args_func()

    options.parse_command_line()
    if options.config:
        options.parse_config_file(options.config)
    # Parse the command line a second time to override config file options
    options.parse_command_line()


def signal_handler(server, app_close, sig, frame):
    """Triggered when a signal is received from system."""
    _ioloop = tornado.ioloop.IOLoop.instance()

    def shutdown():
        """Force server and ioloop shutdown."""
        logger.info('Shuting down server')
        tornado.platform.asyncio.AsyncIOMainLoop().stop()
        if app_close is not None:
            app_close()
        if server is not None:
            server.stop()
        _ioloop.stop()

    logger.warning('Caught signal: %s', sig)
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
