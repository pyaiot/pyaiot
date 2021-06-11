# Copyright 2017 IoT-Lab Team
# Contributor(s) : see AUTHORS file
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Pyaiot COAP EDHOC Initiator module"""

import logging
from binascii import unhexlify

from aiocoap import Context, Message
from aiocoap.numbers.codes import Code

from edhoc.definitions import Correlation, Method, CipherSuite0
from edhoc.roles.edhoc import CoseHeaderMap
from edhoc.roles.initiator import Initiator

from cose.headers import KID

import pyaiot.common.edhoc_keys as edhoc_keys

logger = logging.getLogger("pyaiot.edhoc")

INITIATOR_CONNECTION_ID = b''


async def handshake(addr, cred, authkey):
    """Performs an EDHOC handshake over COAP with remote address <addr>"""
    context = await Context.create_client_context()

    init = Initiator(
        corr=Correlation.CORR_1,
        method=Method.SIGN_SIGN,
        conn_idi=unhexlify(INITIATOR_CONNECTION_ID),
        cred_idi={KID: cred.kid},
        auth_key=authkey,
        cred=cred,
        remote_cred_cb=get_peer_cred,
        supported_ciphers=[CipherSuite0],
        selected_cipher=CipherSuite0,
        ephemeral_key=None)

    msg_1 = init.create_message_one()

    request = Message(code=Code.POST, payload=msg_1,
                      uri=f"coap://{addr}/.well-known/edhoc")

    logging.debug(f"POST ({init.edhoc_state}) {request.payload}")
    response = await context.request(request).response

    logging.debug(f"CHANGED ({init.edhoc_state}), {response.payload}")
    msg_3 = init.create_message_three(response.payload)

    logging.debug(f"POST ({init.edhoc_state}) {request.payload}")
    request = Message(code=Code.POST, payload=msg_3,
                      uri=f"coap://{addr}/.well-known/edhoc")
    response = await context.request(request).response

    init.finalize()
    logging.debug('EDHOC key exchange successfully completed:')

    secret = init.exporter('OSCORE Master Secret', 16)
    salt = init.exporter('OSCORE Master Salt', 8)
    return salt, secret


def get_peer_cred(cred_id: CoseHeaderMap):
    return edhoc_keys.get_peer_cred(cred_id=cred_id)
