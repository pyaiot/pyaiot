"""pyaiot messaging test module."""

import json
from pytest import mark

from pyaiot.common.messaging import Message


@mark.parametrize('message', [1234, "test", "àéèïôû"])
def test_serialize(message):
    serialized = Message.serialize(message)

    assert serialized == json.dumps(message, ensure_ascii=False)


def test_new_node():
    serialized = Message.new_node('1234')

    assert serialized == Message.serialize(
        {'type': 'new', 'uid': '1234', 'dst': 'all'})

    serialized = Message.new_node('1234', '5678')
    assert serialized == Message.serialize(
        {'type': 'new', 'uid': '1234', 'dst': '5678'})


def test_out_node():
    serialized = Message.out_node('1234')

    assert serialized == Message.serialize({'type': 'out', 'uid': '1234'})


def test_reset_node():
    serialized = Message.reset_node('1234')

    assert serialized == Message.serialize({'type': 'reset', 'uid': '1234'})


def test_discover_node():
    serialized = Message.discover_node()

    assert serialized == Message.serialize({'request': 'discover'})


@mark.parametrize('value', [1234, "test", "àéèïôû"])
def test_update_node(value):
    serialized = Message.update_node('1234', 'test', 'value')

    assert serialized == Message.serialize(
        {'type': 'update', 'uid': '1234', 'endpoint': 'test',
         'data': 'value', 'dst': 'all'})

    serialized = Message.update_node('1234', 'test', value, '5678')
    assert serialized == Message.serialize(
        {'type': 'update', 'uid': '1234', 'endpoint': 'test',
         'data': value, 'dst': '5678'})


@mark.parametrize('badvalue', [b"test",
                               bytearray(b"12345"),
                               bytearray("12345".encode('utf-8')),
                               '{"test", "test"}',
                               '{"json": "valid", "content": "invalid"}'])
def test_check_message_bad_json(badvalue):
    message, reason = Message.check_message(badvalue)
    assert message is None
    assert "Invalid message " in reason


def test_check_message_bad_type():
    message, reason = Message.check_message('{"type": "test"}')
    assert message is None
    assert "Invalid message type" in reason


@mark.parametrize('msg_type', ["new", "out", "update", "reset"])
def test_check_message_valid(msg_type):
    to_test = json.dumps({"type": msg_type, "data": "test"})
    message, reason = Message.check_message(to_test)
    assert message is not None
    assert reason is None
