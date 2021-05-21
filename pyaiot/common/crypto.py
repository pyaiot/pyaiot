
"""pyaiot message encryption module"""

import base64
import json
from dataclasses import dataclass, asdict
from typing import ByteString, Any

from cryptography.hazmat.primitives.ciphers.aead import AESCCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from cose import headers
from cose.messages import Enc0Message
from cose.messages import CoseMessage
from cose.algorithms import AESCCM1664128
from cose.keys.keyparam import KpKid, KpAlg
from cose.keys import SymmetricKey


def bxor(ba1: ByteString, ba2: ByteString) -> ByteString:
    """ XOR two byte strings """
    return bytes([_a ^ _b for _a, _b in zip(ba1, ba2)])


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


@dataclass
class CypherMessage:
    ct: str  # bas64 encoded
    aad: str  # base64 encoded

    def to_json_str(self) -> str:
        json_dict = asdict(self)
        return json.dumps(json_dict)

    @staticmethod
    def from_dict(obj: Any) -> 'CypherMessage':
        assert isinstance(obj, dict)
        ct = from_str(obj.get("ct"))
        aad = from_str(obj.get("aad"))
        return CypherMessage(ct, aad)

    @staticmethod
    def from_json_str(json_string: str):
        json_dict = json.loads(json_string)
        return CypherMessage.from_dict(json_dict)

    @property
    def ct_bas64_decode(self) -> ByteString:
        return base64.b64decode(self.ct.encode('utf-8'))

    @property
    def aad_bas64_decode(self) -> ByteString:
        return base64.b64decode(self.aad.encode('utf-8'))


class CryptoCtx():
    NONCE_LENGTH = 13
    COMMON_IV_LENGTH = 13
    AES_CCM_KEY_LENGTH = 16  # 128 bits
    AES_CCM_TAG_LENGTH_BYTES = 8  # 64bits
    CTX_ID_MAX_LEN = 6

    def __init__(self, send_ctx_id: ByteString, recv_ctx_id: ByteString):
        self.send_ctx_key = None
        self.recv_ctx_key = None
        self.common_iv = None
        self.seq_nr = 0
        self.send_ctx_id = send_ctx_id
        self.recv_ctx_id = recv_ctx_id

    @staticmethod
    def __aes_ccm_key(salt: ByteString, secret: ByteString, info: ByteString,
                      length: int = AES_CCM_KEY_LENGTH) -> ByteString:
        hkdf = HKDF(algorithm=hashes.SHA256(), salt=salt, info=info,
                    length=length)
        key = hkdf.derive(secret)
        hkdf = HKDF(algorithm=hashes.SHA256(), salt=salt, info=info,
                    length=length)
        hkdf.verify(secret, key)
        return key

    def encrypt(self, data: ByteString, aad: ByteString) -> ByteString:
        """Encrypts plaintext"""
        nonce = self.gen_nonce(self.send_ctx_id)
        aesccm = AESCCM(self.send_ctx_key, self.AES_CCM_TAG_LENGTH_BYTES)
        return aesccm.encrypt(nonce, data, aad)

    def decrypt(self, cdata: ByteString, aad: ByteString) -> ByteString:
        """Decrypt aes CCM cyphered data"""
        nonce = self.gen_nonce(self.recv_ctx_id)
        aesccm = AESCCM(self.recv_ctx_key, self.AES_CCM_TAG_LENGTH_BYTES)
        return aesccm.decrypt(nonce, cdata, aad)

    def gen_nonce(self, ctx_id: ByteString) -> ByteString:
        """Generates a nonce for a specific context id, sequence number
        is incremented after generating the nonce"""
        pad_seq_nr = list(self.seq_nr.to_bytes(5, byteorder='big'))
        pad_ctx_id = (self.NONCE_LENGTH - 5 - len(ctx_id)) * [0] + list(ctx_id)
        partial_iv = bytes(pad_ctx_id + pad_seq_nr)
        self.seq_nr += 1
        return bxor(self.common_iv, partial_iv)

    def generate_aes_ccm_keys(self, salt: ByteString,
                              secret: ByteString) -> None:
        """Generates recv_ctx_key, send_ctx_key and common_iv from"""
        self.recv_ctx_key = CryptoCtx.__aes_ccm_key(salt, secret,
                                                    self.recv_ctx_id)
        self.send_ctx_key = CryptoCtx.__aes_ccm_key(salt, secret,
                                                    self.send_ctx_id)
        self.common_iv = CryptoCtx.__aes_ccm_key(salt, secret, b'',
                                                 length=self.COMMON_IV_LENGTH)

    def create_msg(self, plain_text: str) -> str:
        """Encrypts plaintext data and returns a JSON string CypherMessage"""
        # convert from string to ByteString
        pt = plain_text.encode('utf-8')
        aad = str(self.seq_nr).encode('utf-8')
        # encrypt and base64 encode for serialization
        ct = self.encrypt(pt, aad)
        ct_b64_s = base64.b64encode(ct).decode('utf-8')
        aad_b64_s = base64.b64encode(aad).decode('utf-8')
        return CypherMessage(ct_b64_s, aad_b64_s).to_json_str()

    def parse_msg(self, msg: str) -> str:
        """Parses a received encrypted messaged and returns the plain
        text data"""
        cm = CypherMessage.from_json_str(msg)
        aad = cm.aad_bas64_decode
        ct = cm.ct_bas64_decode
        pt = self.decrypt(ct, aad)
        return pt.decode('utf-8')

    def decrypt_msg(self, msg: ByteString) -> str:
        """Returns a decoded COSE Encrypt0 message"""
        cose_msg = CoseMessage.decode(msg)
        cose_key = SymmetricKey(self.recv_ctx_key,
                                optional_params={
                                    KpKid: self.recv_ctx_id,
                                    KpAlg: AESCCM1664128
                                })
        cose_msg.key = cose_key
        return cose_msg.decrypt().decode('ascii')

    def encrypt_msg(self, msg: str) -> ByteString:
        """Returns a CBOR-encoded COSE Encrypt0 message"""
        msg = Enc0Message(
            phdr={headers.Algorithm: AESCCM1664128},
            uhdr={headers.IV: self.gen_nonce(self.send_ctx_id)},
            payload=msg.encode('ascii')
        )
        cose_key = SymmetricKey(self.send_ctx_key,
                                optional_params={
                                    KpKid: self.send_ctx_id,
                                    KpAlg: AESCCM1664128
                                })
        msg.key = cose_key
        return msg.encode()
