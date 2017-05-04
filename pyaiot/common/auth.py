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

"""Pyaiot messaging utility module."""

import os.path
import string
import configparser
from collections import namedtuple
from random import choice
from cryptography.fernet import Fernet

DEFAULT_KEY_FILENAME = "{}/.pyaiot/keys".format(os.path.expanduser("~"))
CREDENTIALS_FILENAME = ("{}/.pyaiot/credentials"
                        .format(os.path.expanduser("~")))

Keys = namedtuple('Keys', ['private', 'secret'])
Credentials = namedtuple('Credentials', ['username', 'password'])


def generate_secret_key():
    """Generate a 32 length random secret key with letter and digits."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(choice(alphabet) for i in range(32))


def generate_private_key():
    """Generate a base64-encoded 32-byte private secret key."""
    return Fernet.generate_key().decode()


def write_keys_to_file(filename, keys):
    """Write secret and private key to filename."""
    config = configparser.ConfigParser()
    config['keys'] = {'secret': keys.secret, 'private': keys.private}
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename), mode=0o700)

    with open(filename, 'w') as f:
        config.write(f)


def check_key_file(filename=DEFAULT_KEY_FILENAME):
    """Verify that key filename exists and is correctly formatted."""
    filename = os.path.expanduser(filename)
    if not os.path.isfile(filename):
        raise ValueError("Key file provided doesn't exists: '{}'"
                         .format(filename))

    config = configparser.ConfigParser()
    config.read(filename)

    if (not config.has_option('keys', 'secret') or
            not config.has_option('keys', 'private')):
        raise ValueError("Invalid key file provided: '{}'".format(filename))

    return Keys(private=config['keys']['private'],
                secret=config['keys']['secret'])


def check_credentials_file(filename=CREDENTIALS_FILENAME):
    """Verify that credentials filename exists and is correctly formatted."""
    filename = os.path.expanduser(filename)
    if not os.path.isfile(filename):
        raise ValueError("Credentials file doesn't exists: '{}'"
                         .format(filename))

    config = configparser.ConfigParser()
    config.read(filename)

    if (not config.has_option('credentials', 'username') or
            not config.has_option('credentials', 'password')):
        raise ValueError("Invalid credentials file provided: '{}'"
                         .format(filename))

    return Credentials(username=config['credentials']['username'],
                       password=config['credentials']['password'])


def verify_auth_token(token, keys):
    """Verify the token is valid."""
    return (Fernet(keys.private.encode()).decrypt(token.encode()) ==
            keys.secret.encode())


def auth_token(keys):
    """Generate a token from the given private and secret keys."""
    return Fernet(keys.private.encode()).encrypt(keys.secret.encode())
