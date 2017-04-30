"""One shot Websocket test client."""

import argparse
import json
import websocket


def main(args):
    """Main function."""
    ws = websocket.create_connection("ws://{}:{}/node".format(args.host,
                                                              args.port))
    ws.send(json.dumps({'type': 'new',
                        'data': 'node'}))
    ws.send(json.dumps({'type': 'update',
                        'data': {'node': 'fd00:aaaa:bbbb::1',
                                 'name': 'websocket',
                                 'led': '0',
                                 'os': 'riot'}}))
    print(ws.recv())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Test Websocket node")
    parser.add_argument('--host', type=str, default="localhost",
                        help="Gateway host.")
    parser.add_argument('--port', type=str, default="8001",
                        help="CoGateway port")
    args = parser.parse_args()
    main(args)
