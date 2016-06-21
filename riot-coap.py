import logging
import asyncio

import aiocoap

logging.basicConfig(level=logging.INFO)


@asyncio.coroutine
def main():
    protocol = yield from aiocoap.Context.create_client_context()

    # request = aiocoap.Message(code=aiocoap.PUT, payload="1".encode())
    # request.set_request_uri("coap://[2001:470:c87a:abad:5846:257d:3b04:f9d6]"
    #                         "/led")
    # request = aiocoap.Message(code=aiocoap.GET)
    # request.set_request_uri("coap://[2001:470:c87a:abad:5846:257d:3b04:f9d6]"
    #                         "/temperature")
    request = aiocoap.Message(code=aiocoap.GET)
    request.set_request_uri("coap://[2001:470:c87a:abad:5846:257d:3b04:f9d6]"
                            "/.well-known/core")
    try:
        response = yield from protocol.request(request).response
    except Exception as e:
        print('Failed to fetch resource:')
        print(e)
    else:
        print('Result: %s\n%s' % (response.code, response.payload.decode()))

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
