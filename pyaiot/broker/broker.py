# Copyright 2017 IoT-Lab Team
# Contributor(s) : see AUTHORS file
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Broker application module."""

import sys
import time
import logging
import signal
from functools import partial
import tornado
from tornado.options import define, options
import tornado.platform.asyncio

from pyaiot.common.auth import check_key_file, DEFAULT_KEY_FILENAME

from .application import BrokerApplication

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')
logger = logging.getLogger("pyaiot.broker")


def parse_command_line():
    """Parse command line arguments for IoT broker application."""
    if not hasattr(options, "port"):
        define("port", default=8000, help="Broker websocket port")
    if not hasattr(options, "debug"):
        define("debug", default=False, help="Enable debug mode.")
    if not hasattr(options, "key-file"):
        define("key-file", default=DEFAULT_KEY_FILENAME,
               help="Secret and private keys filename.")
    options.parse_command_line()


def sig_handler(server, sig, frame):
    """Triggered when a signal is received from system."""
    _ioloop = tornado.ioloop.IOLoop.instance()

    def shutdown():
        """Force server and ioloop shutdown."""
        logging.info('Shuting down server')
        server.stop()
        _ioloop.stop()

    logging.warning('Caught signal: %s', sig)
    _ioloop.add_callback_from_signal(shutdown)


def run(arguments=[]):
    """Start a broker instance."""
    if arguments != []:
        sys.argv[1:] = arguments

    parse_command_line()

    if options.debug:
        logger.setLevel(logging.DEBUG)

    try:
        keys = check_key_file(options.key_file)
    except ValueError as e:
        logger.error(e)
        return

    _ioloop = tornado.ioloop.IOLoop.current()
    app = BrokerApplication(keys, options=options)
    _server = app.listen(options.port)

    signal.signal(signal.SIGTERM, partial(sig_handler, _server))
    signal.signal(signal.SIGINT, partial(sig_handler, _server))

    _ioloop.start()
    logger.debug("Application stopped")


if __name__ == '__main__':
    run()
