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

import logging
import asyncio
from aiocoap import Context, Message, POST
from twython import TwythonStreamer

APP_KEY = "sPEoM9ZdkTscxiXLAZVLOmS4j"
APP_SECRET = "TK3xYdOVlEFoCKWppkytodt5nL5J25utIUUA0yOZu6Qhy3Vm0z"
OAUTH_TOKEN = "302547016-i5Cee4x4EMwdMirfGaMbuW5NUiJAu8rNKCalAsBp"
OAUTH_TOKEN_SECRET = "mgiW2xloF7BcygAlT36iHj9XWGKB4wpG0iqMHujIIffqP"

logging.basicConfig(level=logging.INFO)


@asyncio.coroutine
def coap_message(message=None):
    protocol = yield from Context.create_client_context()

    if message is None:
        request = Message(code=POST, payload="Hello Twitter".encode('utf-8'))
        request.set_request_uri('coap://localhost/alive')
    else:
        request = Message(code=POST,
                          payload="twitter:{}".format(message).encode('utf-8'))
        request.set_request_uri('coap://localhost/server')

    try:
        yield from protocol.request(request).response
    except Exception as e:
        print('Failed to fetch resource:')
        print(e)


class RiotTwitterStreamer(TwythonStreamer):
    def on_success(self, data):
        if 'text' in data:
            asyncio.get_event_loop().run_until_complete(
                coap_message(data['text'].replace('\n', ' ')))

    def on_error(self, status_code, data):
        print(status_code)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(coap_message())
    stream = RiotTwitterStreamer(APP_KEY, APP_SECRET,
                                 OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
    stream.statuses.filter(track='RIOT-OS')
