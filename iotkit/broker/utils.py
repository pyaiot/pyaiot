"""Utility functions module."""

import json
from tornado import gen

from .data import coap_nodes, client_sockets
from .logger import logger


def _to_html(string):
    """Convert html special characters."""
    return string\
        .replace('<', '&lt;')\
        .replace('>', '&gt;')


def _endpoints(link_header):
    link = link_header.replace(' ', '')
    return link.split(',')


def _broadcast_message(message):
    """Broadcast message on all opened websockets."""
    logger.debug("Broadcasting message '{}' to web clients.".format(message))
    for ws in client_sockets:
        ws.write_message(message)


@gen.coroutine
def _check_dead_nodes():
    """Find dead nodes in the list of known nodes and remove them."""
    global coap_nodes
    if len(coap_nodes) == 0:
        return

    nodes = []
    for node in coap_nodes:
        if node.active():
            nodes += [node]
        else:
            logger.debug("Removing inactive node {}".format(node.address))
            _broadcast_message(json.dumps({'node': node.address,
                                           'command': 'out'}))
    coap_nodes = nodes
