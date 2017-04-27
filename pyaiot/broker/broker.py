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
import tornado
import logging
from tornado.options import define, options
import tornado.platform.asyncio

from .application import BrokerApplication
from .logger import logger

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')


def parse_command_line():
    """Parse command line arguments for IoT broker application."""
    if not hasattr(options, "port"):
        define("port", default=8000, help="Broker port")
    if not hasattr(options, "max_time"):
        define("max_time", default=120,
               help="Retention time for lost nodes (s).")
    if not hasattr(options, "debug"):
        define("debug", default=False, help="Enable debug mode.")
    options.parse_command_line()

    if options.debug:
        logger.setLevel(logging.DEBUG)


def run(arguments=[]):
    """Start a broker instance."""
    if arguments != []:
        sys.argv[1:] = arguments

    parse_command_line()
    try:
        # Application ioloop initialization
        if not tornado.platform.asyncio.AsyncIOMainLoop().initialized():
            tornado.platform.asyncio.AsyncIOMainLoop().install()

        # Start controller application (Tornado based)
        app = BrokerApplication(options=options)
        app.listen(options.port)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        logger.debug("Stopping application")
        tornado.ioloop.IOLoop.instance().stop()

if __name__ == '__main__':
    run()
