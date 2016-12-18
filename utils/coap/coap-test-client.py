import logging
import asyncio
import argparse
from aiocoap import Context, Message, POST

logging.basicConfig(level=logging.INFO)


@asyncio.coroutine
def alive_message(args):
    path = args.alive
    payload = args.payload,
    server = args.server

    protocol = yield from Context.create_client_context()

    if path == "alive":
        request = Message(code=POST, payload="Alive".encode('utf-8'))
        request.set_request_uri('coap://{}/{}'.format(server, path))
    else:
        request = Message(code=POST, payload=payload.encode('utf-8'))
        request.set_request_uri('coap://{}/server'.format(server))

    try:
        yield from protocol.request(request).response
    except Exception as e:
        print('Failed to fetch resource:')
        print(e)


def main():
    parser = argparse.ArgumentParser(description="Test CoAP client")
    parser.add_argument('--server', type=str, default="localhost",
                        help="Server host.")
    parser.add_argument('--path', type=str, default="alive",
                        help="CoAP resource path")
    parser.add_argument('--payload', type=str, default="",
                        help="CoAP resource payload")
    args = parser.parse_args()
    asyncio.get_event_loop().run_until_complete(alive_message(args))

if __name__ == "__main__":
    main()
