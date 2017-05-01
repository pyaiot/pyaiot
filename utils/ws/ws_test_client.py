"""One shot Websocket test client."""

import sys
import argparse
import json
import websocket

from pyaiot.common.messaging import Message


def init_node(ws):
    """Send initial node information"""
    ws.send(json.dumps({'type': 'update',
                        'data': {'node': 'fd00:aaaa:bbbb::1',
                                 'name': 'websocket',
                                 'led': '0',
                                 'os': 'riot'}}))


def main(args):
    """Main function."""
    try:
        ws = websocket.create_connection("ws://{}:{}/node".format(args.host,
                                                                  args.port))
    except ConnectionRefusedError:
        print("Cannot connect to ws://{}:{}".format(args.host, args.port))
        return

    ws.send(json.dumps({'type': 'new', 'data': 'node'}))
    init_node(ws)
    while True:
        try:
            msg = ws.recv()
        except:
            print("Connection closed")
            break
        else:
            print(msg)
            if msg == Message.discover_node():
                init_node(ws)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Test Websocket node")
    parser.add_argument('--host', type=str, default="localhost",
                        help="Gateway host.")
    parser.add_argument('--port', type=str, default="8001",
                        help="CoGateway port")
    args = parser.parse_args()
    try:
        main(args)
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit()
