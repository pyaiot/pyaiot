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

"""CoAP gateway application module."""

import sys
import logging
import tornado.platform.asyncio
from tornado.options import define, options

from pyaiot.common.auth import check_key_file, DEFAULT_KEY_FILENAME
from pyaiot.common.helpers import start_application

from .coap import MAX_TIME, COAP_PORT, COAPS_PORT
from .application import CoapGatewayApplication

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)14s - '
                           '%(levelname)5s - %(message)s')
logger = logging.getLogger("pyaiot.gw.coap")


def parse_command_line():
    """Parse command line arguments for CoAP gateway application."""
    if not hasattr(options, "broker_host"):
        define("broker_host", default="localhost", help="Broker host")
    if not hasattr(options, "broker_port"):
        define("broker_port", default=8000, help="Broker port")
    if not hasattr(options, "coap-port"):
        define("coap-port", default=COAP_PORT,
               help="Gateway CoAP server port")
    if not hasattr(options, "coaps-port"):
        define("coaps-port", default=COAPS_PORT,
               help="Gateway CoAP server secure port")
    if not hasattr(options, "max_time"):
        define("max_time", default=MAX_TIME,
               help="Maximum retention time (in s) for CoAP dead nodes")
    if not hasattr(options, "key-file"):
        define("key-file", default=DEFAULT_KEY_FILENAME,
               help="Secret and private keys filename.")
    if not hasattr(options, "debug"):
        define("debug", default=False, help="Enable debug mode.")
    if not hasattr(options, "use-coaps"):
        define("use-coaps", default=False, help="Enable CoAP Secure.")
    options.parse_command_line()


def run(arguments=[]):
    """Start the CoAP gateway instance."""
    if arguments != []:
        sys.argv[1:] = arguments

    parse_command_line()

    if options.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("pyaiot.gw.client").setLevel(logging.DEBUG)

    try:
        keys = check_key_file(options.key_file)
    except ValueError as e:
        logger.error(e)
        return

    if not tornado.platform.asyncio.AsyncIOMainLoop().initialized():
        tornado.platform.asyncio.AsyncIOMainLoop().install()

    start_application(CoapGatewayApplication(keys, options=options),
                      port=options.coap_port, close_client=True)


if __name__ == '__main__':
    run()
