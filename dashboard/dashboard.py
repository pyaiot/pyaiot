import os
import sys
import os.path
import tornado
import logging
import asyncio
from tornado import web
from tornado.options import define, options
import tornado.platform.asyncio

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')
internal_logger = logging.getLogger("tornado.internal")


class DashboardHandler(web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, path=None):
        self.render("dashboard.html",
                    wsserver="{}:{}".format(options.broker_host,
                                            options.broker_port),
                    camera_url=options.camera_url,
                    favicon=options.favicon,
                    logo_url=options.dashboard_logo,
                    title=options.dashboard_title)


class IoTDashboardApplication(web.Application):
    """Tornado based web application providing an IoT Dashboard."""

    def __init__(self):
        self._nodes = {}
        self._log = logging.getLogger("iot dashboard")
        if options.debug:
            self._log.setLevel(logging.DEBUG)

        handlers = [
            (r'/', DashboardHandler),
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
                       .format(options.port))


def parse_command_line():
    """Parse command line arguments for IoT broker application."""

    define("port", default=8080,
           help="Web application HTTP port")
    define("broker_port", default=8080,
           help="Broker port")
    define("broker_host", default="localhost",
           help="Broker hostname")
    define("camera_url", default="/demo-cam/?action=stream",
           help="Default camera url")
    define("dashboard_title", default="IoT Dashboard",
           help="Dashboard title")
    define("dashboard_logo", default="/static/assets/logo-riot.png",
           help="Logo for dashboard title")
    define("favicon", default="/static/assets/favicon192.png",
           help="Favicon url for your dashboard site")
    define("debug", default=False,
           help="Enable debug mode.")
    options.parse_command_line()

    if options.debug:
        internal_logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    parse_command_line()
    try:
        ioloop = asyncio.get_event_loop()
        tornado.platform.asyncio.AsyncIOMainLoop().install()

        # Start tornado application
        app = IoTDashboardApplication()
        app.listen(options.port)
        ioloop.run_forever()
    except KeyboardInterrupt:
        print("Exiting")
        ioloop.stop()
        sys.exit()
