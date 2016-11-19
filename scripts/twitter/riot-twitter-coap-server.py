import logging
import asyncio

import aiocoap.resource as resource
import aiocoap


class RiotTwitterResource(resource.Resource):
    """RIOT Twitter resource."""
    def __init__(self):
        super(RiotTwitterResource, self).__init__()

    @asyncio.coroutine
    def render_get(self, request):
        payload = "Riot Demo Twitter stream"
        return aiocoap.Message(code=aiocoap.CONTENT, payload=payload)


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)14s - '
                    '%(levelname)5s - %(message)s')
logging.getLogger("coap-server").setLevel(logging.DEBUG)


def main():
    # Resource tree creation
    root = resource.Site()
    root.add_resource(('twitter', ), RiotTwitterResource())
    root.add_resource(('.well-known', 'core'),
                      resource.WKCResource(root.get_resources_as_linkheader))
    asyncio.async(aiocoap.Context.create_server_context(root))

    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    main()
