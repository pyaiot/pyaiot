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

"""Web dashboard tornado application module"""

import os
import sys
import os.path
import tornado
import logging
import asyncio
import tornado.platform.asyncio
from tornado import web
from tornado.options import define, options

from pyaiot.common.auth import (check_credentials_file, CREDENTIALS_FILENAME,
                                Credentials, check_key_file,
                                DEFAULT_KEY_FILENAME, auth_token)


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')
logger = logging.getLogger("pyaiot.dashboard")


class BaseHandler(web.RequestHandler):

    def get_current_user(self):
        if options.insecure:
            return "user"

        username = self.get_secure_cookie("username")
        password = self.get_secure_cookie("password")
        if username is None or password is None:
            return None
        username = username.decode()
        password = password.decode()
        if (username != self.application.username or
                password != self.application.password):
            return None

        return username


class LoginHandler(BaseHandler):

    def _render(self, error=None):
        self.render("login.html",
                    error=error,
                    favicon=options.favicon,
                    logo_url=options.logo,
                    title=options.title)

    def get(self):
        if options.insecure:
            self.redirect("/")
        else:
            self._render()

    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")

        if (username == self.application.username and
                password == self.application.password):
            self.set_secure_cookie("username", username)
            self.set_secure_cookie("password", password)
            self.redirect(self.get_argument("next", "/"))
        else:
            self._render(error="Invalid username or password")


class DashboardHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.web.authenticated
    def get(self, path=None):
        self.render("dashboard.html",
                    wsserver="{}:{}".format(options.broker_host,
                                            options.broker_port),
                    camera_url=options.camera_url,
                    favicon=options.favicon,
                    logo_url=options.logo,
                    title=options.title,
                    mtoken=auth_token(self.application.keys))


class IoTDashboardApplication(web.Application):
    """Tornado based web application providing an IoT Dashboard."""

    def __init__(self, credentials, keys):
        self._nodes = {}
        self.username = credentials.username
        self.password = credentials.password
        self.keys = keys
        if options.debug:
            logger.setLevel(logging.DEBUG)

        handlers = [
            (r'/', DashboardHandler),
            (r"/login", LoginHandler)
        ]

        settings = dict(debug=True,
                        cookie_secret="MY_COOKIE_ID",
                        xsrf_cookies=True,
                        static_path=options.static_path,
                        template_path=options.static_path,
                        login_url="/login"
                        )

        super().__init__(handlers, **settings)
        logger.info('Application started, listening on port {0}'
                    .format(options.port))


def parse_command_line():
    """Parse command line arguments for IoT broker application."""
    define("static-path",
           default=os.path.join(os.path.dirname(__file__), "static"),
           help="Static files path (containing npm package.json file)")
    define("port", default=8080,
           help="Web application HTTP port")
    define("broker_port", default=8000,
           help="Broker port")
    define("broker_host", default="localhost",
           help="Broker hostname")
    define("camera_url", default=None,
           help="Default camera url")
    define("title", default="IoT Dashboard",
           help="Dashboard title")
    define("logo", default=None,
           help="URL for a logo in the dashboard navbar")
    define("favicon", default=None,
           help="Favicon url for your dashboard site")
    define("key-file", default=DEFAULT_KEY_FILENAME,
           help="Secret and private keys filename.")
    define("insecure", default=False,
           help="Start the dashboard in insecure mode (no login required).")
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

    try:
        keys = check_key_file(options.key_file)
    except ValueError as e:
        logger.error(e)
        return

    try:
        credentials = check_credentials_file(CREDENTIALS_FILENAME)
    except:
        credentials = Credentials(username="default", password="default")

    try:
        ioloop = asyncio.get_event_loop()
        tornado.platform.asyncio.AsyncIOMainLoop().install()

        # Start tornado application
        app = IoTDashboardApplication(credentials, keys)
        app.listen(options.port)
        ioloop.run_forever()
    except KeyboardInterrupt:
        print("Exiting")
        ioloop.stop()


if __name__ == '__main__':
    run()
