"""pyaiot crypto test module."""

from pyaiot.common.crypto import CryptoCtx, CypherMessage

ALICE_ID = b'\xcc\xd1'
BOB_ID = b'\xac\xe2'
SALT = b'\xea\xea\xd4H\xe0V\xef\x83'
SECRET = b'\x16lE\xab\xb8\xd6\xdb\xe5\xd7q\xeb\x1d\x8b !\xa4'

PLAIN_TEXT = b"a secret message"
AAD_DATA = b"authenticated but unencrypted data"

PLAIN_TEXT_STRING = "a secret message"
CYPHER_MESSAGE_STRING = "{\"ct\": \"ct\", \"aad\": \"aad\"}"


def test_generate_keys_bob_alice_match():
    """Basic test, generated aes-ccm keys should match"""
    bob = CryptoCtx(BOB_ID, ALICE_ID)
    alice = CryptoCtx(ALICE_ID, BOB_ID)
    bob.generate_aes_ccm_keys(SALT, SECRET)
    alice.generate_aes_ccm_keys(SALT, SECRET)

    assert bob.common_iv == alice.common_iv
    assert bob.send_ctx_key == alice.recv_ctx_key
    assert alice.send_ctx_key == bob.recv_ctx_key


def test_bob_alice_encrypt_decrypt():
    """Test AES-CCM encryption decryption"""
    bob = CryptoCtx(BOB_ID, ALICE_ID)
    alice = CryptoCtx(ALICE_ID, BOB_ID)
    bob.generate_aes_ccm_keys(SALT, SECRET)
    alice.generate_aes_ccm_keys(SALT, SECRET)
    cypher_text = bob.encrypt(PLAIN_TEXT, AAD_DATA)
    plain_text = alice.decrypt(cypher_text, AAD_DATA)
    assert plain_text == PLAIN_TEXT


def test_cypher_message_new_parse():
    """Create a new encrypted message and decode a received message"""
    bob = CryptoCtx(BOB_ID, ALICE_ID)
    alice = CryptoCtx(ALICE_ID, BOB_ID)
    bob.generate_aes_ccm_keys(SALT, SECRET)
    alice.generate_aes_ccm_keys(SALT, SECRET)
    message = bob.create_msg(PLAIN_TEXT_STRING)
    plain_text = alice.parse_msg(message)
    assert plain_text == PLAIN_TEXT_STRING


def test_cypher_message_to_json_str():
    """Convert CypherMessage to json string"""
    cypher_msg = CypherMessage("ct", "aad")
    cypher_msg_str = cypher_msg.to_json_str()
    assert cypher_msg_str == CYPHER_MESSAGE_STRING


def test_cypher_messsage_from_json_string():
    """Test convertion of CypherMessage from JSON string"""
    cypher_msg = CypherMessage.from_json_str(CYPHER_MESSAGE_STRING)
    assert cypher_msg.aad == "aad"
    assert cypher_msg.ct == "ct"


def test_crypto_encrypt_decrypt_msg():
    """Test cose encryption decryption of a message"""
    bob = CryptoCtx(BOB_ID, ALICE_ID)
    alice = CryptoCtx(ALICE_ID, BOB_ID)
    bob.generate_aes_ccm_keys(SALT, SECRET)
    alice.generate_aes_ccm_keys(SALT, SECRET)
    encoded_msg = bob.encrypt_msg(PLAIN_TEXT_STRING)
    decoded_msg = alice.decrypt_msg(encoded_msg)
    assert decoded_msg == PLAIN_TEXT_STRING
