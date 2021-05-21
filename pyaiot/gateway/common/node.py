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

"""Class for managed node."""

import logging
import time

from pyaiot.common.crypto import CryptoCtx

logger = logging.getLogger("pyaiot.gw.common.node")


class Node():
    """Class for managed nodes."""

    GW_RECV_CTX_ID = b'\xea\xea\xd4H\xe0V\xef\x83'

    def __init__(self, uid, **default_resources):
        self.uid = uid
        self.last_seen = time.time()
        self.ctx = CryptoCtx(self.GW_RECV_CTX_ID, uid.encode('utf-8'))
        self.resources = default_resources

    def __eq__(self, other):
        return self.uid == other.uid

    def __gt__(self, other):
        return self.uid > other.uid

    def __repr__(self):
        return "Node <{}>".format(self.uid)

    def update_last_seen(self):
        self.last_seen = time.time()

    def set_resource_value(self, resource, value):
        if resource not in self.resources:
            self.resources.update({resource: value})
        else:
            self.resources[resource] = value

    def clear_resources(self):
        self.resources = {}

    def has_crypto_ctx(self):
        return self.ctx.recv_ctx_key != None
