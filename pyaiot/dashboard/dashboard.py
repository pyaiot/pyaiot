#!/usr/bin/env python

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

"""Web dashboard tornado application module."""

import os
import os.path
import sys
import logging
import tornado
from tornado import web
from tornado.options import define, options

from pyaiot.common.helpers import start_application

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')
logger = logging.getLogger("pyaiot.dashboard")


class DashboardHandler(web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, path=None):
        self.render("dashboard.html",
                    wsproto="wss" if options.broker_ssl else "ws",
                    wsserver="{}:{}".format(options.broker_host,
                                            options.broker_port),
                    camera_url=options.camera_url,
                    favicon=options.favicon,
                    logo_url=options.logo,
                    title=options.title)


class IoTDashboardApplication(web.Application):
    """Tornado based web application providing an IoT Dashboard."""

    def __init__(self):
        self._nodes = {}
        if options.debug:
            logger.setLevel(logging.DEBUG)

        handlers = [
            (r'/', DashboardHandler),
        ]
        settings = {'debug': True,
                    "cookie_secret": "MY_COOKIE_ID",
                    "xsrf_cookies": False,
                    'static_path': options.static_path,
                    'template_path': options.static_path
                    }
        super().__init__(handlers, **settings)
        logger.info('Application started, listening on port {0}'
                    .format(options.port))


def parse_command_line():
    """Parse command line arguments for IoT broker application."""
    if not hasattr(options, "static-path"):
        define("static-path",
               default=os.path.join(os.path.dirname(__file__), "static"),
               help="Static files path (containing npm package.json file)")
    if not hasattr(options, "port"):
        define("port", default=8080,
               help="Web application HTTP port")
    if not hasattr(options, "broker-port"):
        define("broker_port", default=8000,
               help="Broker port")
    if not hasattr(options, "broker-host"):
        define("broker_host", default="localhost",
               help="Broker hostname")
    if not hasattr(options, "broker_ssl"):
        define("broker_ssl", type=bool, default=False,
               help="Supply the broker websocket with ssl")
    if not hasattr(options, "camera_url"):
        define("camera_url", default=None,
               help="Default camera url")
    if not hasattr(options, "title"):
        define("title", default="IoT Dashboard",
               help="Dashboard title")
    if not hasattr(options, "logo"):
        define("logo", default=None,
               help="URL for a logo in the dashboard navbar")
    if not hasattr(options, "favicon"):
        define("favicon", default=None,
               help="Favicon url for your dashboard site")
    if not hasattr(options, "debug"):
        define("debug", default=False,
               help="Enable debug mode.")
    options.parse_command_line()


def run(arguments=[]):
    """Start an instance of a dashboard."""
    if arguments != []:
        sys.argv[1:] = arguments

    parse_command_line()

    if options.debug:
        logger.setLevel(logging.DEBUG)

    start_application(IoTDashboardApplication(), port=options.port)


if __name__ == '__main__':
    run()
