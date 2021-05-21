"""pyaiot auth test module."""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cose.keys import OKPKey
from cose.headers import KID

import pyaiot.common.edhoc_keys as edhoc_keys


RSA_PEM_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQCqGKukO1De7zhZj6+H0qtjTkVxwTCpvKe4eCZ0FPqri0cb2JZfXJ/DgYSF6vUp
wmJG8wVQZKjeGcjDOL5UlsuusFncCzWBQ7RKNUSesmQRMSGkVb1/3j+skZ6UtW+5u09lHNsj6tQ5
1s1SPrCBkedbNf0Tp0GbMJDyR4e9T04ZZwIDAQABAoGAFijko56+qGyN8M0RVyaRAXz++xTqHBLh
3tx4VgMtrQ+WEgCjhoTwo23KMBAuJGSYnRmoBZM3lMfTKevIkAidPExvYCdm5dYq3XToLkkLv5L2
pIIVOFMDG+KESnAFV7l2c+cnzRMW0+b6f8mR1CJzZuxVLL6Q02fvLi55/mbSYxECQQDeAw6fiIQX
GukBI4eMZZt4nscy2o12KyYner3VpoeE+Np2q+Z3pvAMd/aNzQ/W9WaI+NRfcxUJrmfPwIGm63il
AkEAxCL5HQb2bQr4ByorcMWm/hEP2MZzROV73yF41hPsRC9m66KrheO9HPTJuo3/9s5p+sqGxOlF
L0NDt4SkosjgGwJAFklyR1uZ/wPJjj611cdBcztlPdqoxssQGnh85BzCj/u3WqBpE2vjvyyvyI5k
X6zk7S0ljKtt2jny2+00VsBerQJBAJGC1Mg5Oydo5NwD6BiROrPxGo2bpTbu/fhrT8ebHkTz2epl
U9VQQSQzY1oZMVX8i1m5WUTLPz2yLJIBQVdXqhMCQBGoiuSoSjafUhV7i1cEGpb88h5NBYZzWXGZ
37sJ5QsW+sJyoNde3xH8vdXhzU7eT82D6X/scw9RZz+/6rCJ4p0=
-----END RSA PRIVATE KEY-----
"""


def test_write_edhoc_credentials(tmp_path):
    authkey_path = tmp_path / "authkey.pem"
    authcred_path = tmp_path / "cred.pem"
    authkey = edhoc_keys.generate_ed25519_priv_key()
    edhoc_keys.write_edhoc_credentials(authkey, authkey_path,
                                       authcred_path)
    file_authkey = edhoc_keys.parse_edhoc_authkey_file(authkey_path)
    file_authcred = edhoc_keys.parse_edhoc_authcred_file(authcred_path)
    assert file_authkey.d == authkey.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption())
    authcred = authkey.public_key()
    assert file_authcred.x == authcred.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw)


def test_parse_key_wrong_type(tmp_path):
    path = tmp_path / "wrongkey.pem"
    path.write_text(RSA_PEM_KEY)
    with pytest.raises(TypeError):
        edhoc_keys.parse_key(path)


def test_parse_key_invalid_key(tmp_path):
    path = tmp_path / "wrongkey.pem"
    path.write_text("asdfasdf")
    with pytest.raises(ValueError):
        edhoc_keys.parse_key(path)


def test_get_edhoc_keys(tmp_path):
    authkey_path = tmp_path / "authkey.pem"
    authcred_path = tmp_path / "cred.pem"
    authkey = edhoc_keys.generate_ed25519_priv_key()
    edhoc_keys.write_edhoc_credentials(authkey, authkey_path,
                                       authcred_path)
    creds = edhoc_keys.get_edhoc_keys(authcred_path, authkey_path)
    assert isinstance(creds.authkey, OKPKey)
    assert isinstance(creds.authcred, OKPKey)


def test_add_peer_cred(tmp_path):
    path = tmp_path / "peercred"
    cred1 = "0zwe1YPaPxdq3fOtQPkzvvDoiOyPOo1jTmJMgnpo2SA="
    cred2 = "YF/5Nehu2apKdzIgC97gmp+iWFYs0JB4DnFFNbF2zFo="
    assert edhoc_keys.add_peer_cred(cred1, b'20', path)
    assert not edhoc_keys.add_peer_cred(cred1, b'20', path)
    assert edhoc_keys.add_peer_cred(cred2, b'21', path)


def test_rmv_peer_cred(tmp_path):
    path = tmp_path / "peercred"
    cred1 = b'\xd3<\x1e\xd5\x83\xda?\x17j\xdd\xf3\xad@\xf93\xbe\xf0\xe8\x88\xec\x8f:\x8dcNbL\x82zh\xd9 '
    cred2 = b'`_\xf95\xe8n\xd9\xaaJw2 \x0b\xde\xe0\x9a\x9f\xa2XV,\xd0\x90x\x0eqE5\xb1v\xccZ'
    assert edhoc_keys.add_peer_cred(cred1, b'20', path)
    assert edhoc_keys.add_peer_cred(cred2, b'21', path)
    assert edhoc_keys.rmv_peer_cred(b'20', path)
    assert edhoc_keys.rmv_peer_cred(b'21', path)
    assert not edhoc_keys.rmv_peer_cred(b'20', path)


def test_get_peer_cred(tmp_path):
    path = tmp_path / "peercred"
    cred1 = b'\xd3<\x1e\xd5\x83\xda?\x17j\xdd\xf3\xad@\xf93\xbe\xf0\xe8\x88\xec\x8f:\x8dcNbL\x82zh\xd9 '
    cred2 = b'`_\xf95\xe8n\xd9\xaaJw2 \x0b\xde\xe0\x9a\x9f\xa2XV,\xd0\x90x\x0eqE5\xb1v\xccZ'
    assert edhoc_keys.add_peer_cred(cred1, b'20', path)
    assert edhoc_keys.add_peer_cred(cred2, b'21', path)
    key = edhoc_keys.get_peer_cred({KID.identifier: b'20'}, path)
    assert key.kid == b'20'
    assert key.x == cred1
    key = edhoc_keys.get_peer_cred({KID.identifier: b'22'}, path)
    assert key == None
