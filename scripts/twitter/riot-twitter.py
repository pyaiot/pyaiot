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
    stream.statuses.filter(track='Paris')
