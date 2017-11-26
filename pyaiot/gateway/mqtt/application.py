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

"""MQTT gateway application module."""

import sys
import logging
import tornado.platform.asyncio
from tornado.options import define, options

from pyaiot.common.auth import check_key_file
from pyaiot.common.helpers import start_application, parse_command_line

from .gateway import MQTTGateway, MAX_TIME, MQTT_PORT, MQTT_HOST

logger = logging.getLogger("pyaiot.gw.mqtt")


def extra_args():
    """Parse command line arguments for CoAP gateway application."""
    if not hasattr(options, "mqtt_host"):
        define("mqtt_host", default=MQTT_HOST, help="Gateway MQTT broker host")
    if not hasattr(options, "mqtt_port"):
        define("mqtt_port", default=MQTT_PORT, help="Gateway MQTT broker port")
    if not hasattr(options, "max_time"):
        define("max_time", default=MAX_TIME,
               help="Maximum retention time (in s) for MQTT dead nodes")


def run(arguments=[]):
    """Start the CoAP gateway instance."""
    if arguments != []:
        sys.argv[1:] = arguments
    try:
        parse_command_line(extra_args_func=extra_args)
    except SyntaxError as exc:
        logger.error("Invalid config file: {}".format(exc))
        return
    except FileNotFoundError as exc:
        logger.error("Config file not found: {}".format(exc))
        return

    try:
        keys = check_key_file(options.key_file)
    except ValueError as exc:
        logger.error(exc)
        return

    # Application ioloop initialization
    if not tornado.platform.asyncio.AsyncIOMainLoop().initialized():
        tornado.platform.asyncio.AsyncIOMainLoop().install()

    start_application(MQTTGateway(keys, options=options),
                      close_client=True)


if __name__ == '__main__':
    run()
