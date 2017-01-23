import sys
import tornado
import asyncio
import logging
from tornado.ioloop import PeriodicCallback
from tornado.options import define, options
import tornado.platform.asyncio

from .application import BrokerApplication
from .coap import coap_server_init
from .logger import logger
from .utils import _check_dead_nodes

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')


def parse_command_line():
    """Parse command line arguments for IoT broker application."""
    define("port", default=8000,
           help="Broker port")
    define("max_time", default=120,
           help="Retention time for lost nodes (s).")
    define("debug", default=False,
           help="Enable debug mode.")
    options.parse_command_line()

    if options.debug:
        logger.setLevel(logging.DEBUG)


def run():
    """Start a broker instance."""
    parse_command_line()
    try:
        # Tornado ioloop initialization
        ioloop = asyncio.get_event_loop()
        tornado.platform.asyncio.AsyncIOMainLoop().install()
        PeriodicCallback(_check_dead_nodes, 1000).start()

        # Initialize Coap server
        coap_server_init(options.max_time)

        # Start tornado application
        app = BrokerApplication(options=options)
        app.listen(options.port)
        ioloop.run_forever()
    except KeyboardInterrupt:
        print("Exiting")
        ioloop.stop()
        sys.exit()


if __name__ == '__main__':
    run()
