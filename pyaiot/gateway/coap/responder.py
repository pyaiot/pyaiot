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

"""Pyaiot COAP EDHOC Responder module"""

import logging
from binascii import unhexlify

import aiocoap
import aiocoap.resource as resource

from edhoc.definitions import CipherSuite, EdhocState, CipherSuite0
from edhoc.exceptions import EdhocException
from edhoc.roles.edhoc import CoseHeaderMap
from edhoc.roles.responder import Responder

from cose.headers import KID

from pyaiot.common.crypto import CryptoCtx
import pyaiot.common.edhoc_keys as auth

import logging

logger = logging.getLogger("pyaiot.edhoc")

DEFAULT_CONNECTION_ID = b'2b'


class EdhocResource(resource.Resource):
    def __init__(self, cred, auth_key, crypto_ctx=None):
        super(EdhocResource, self).__init__()
        self.cred_idr = {KID: cred.kid}
        self.cred = cred
        self.auth_key = auth_key
        self.supported = [CipherSuite0]
        self.crypto_ctx = crypto_ctx
        self.resp = self.create_responder()

    @classmethod
    def get_peer_cred(cls, cred_id: CoseHeaderMap):
        return auth.get_peer_cred(cred_id=cred_id)

    def create_responder(self):
        return Responder(conn_idr=unhexlify(DEFAULT_CONNECTION_ID),
                         cred_idr=self.cred_idr,
                         auth_key=self.auth_key,
                         cred=self.cred,
                         remote_cred_cb=self.get_peer_cred,
                         supported_ciphers=[CipherSuite0],
                         ephemeral_key=None)

    async def render_post(self, request):
        if self.resp.edhoc_state == EdhocState.EDHOC_WAIT:
            logger.info('EDHOC got message 2')
            msg_2 = self.resp.create_message_two(request.payload)
            return aiocoap.Message(code=aiocoap.Code.CHANGED, payload=msg_2)

        elif self.resp.edhoc_state == EdhocState.MSG_2_SENT:
            self.resp.finalize(request.payload)
            logger.debug('EDHOC key exchange successfully completed:')

            if self.crypto_ctx:
                secret = self.resp.exporter('OSCORE Master Secret', 16)
                salt = self.resp.exporter('OSCORE Master Salt', 8)
                self.crypto_ctx.generate_aes_ccm_keys(salt, secret)

            # initialize new Responder object
            self.resp = self.create_responder()

            return aiocoap.Message(code=aiocoap.Code.CHANGED)
        else:
            raise EdhocException(f"Illegal state: {self.resp.edhoc_state}")
