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

"""iot-kit package installation module."""

import os
from os.path import join as pjoin
from setuptools import setup


PACKAGE = 'pyaiot'


def readme(fname):
    """Utility function to read the README. Used for long description."""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def get_version(package):
    """Extract package version without importing file.

    Inspired from pep8 setup.py.
    """
    with open(os.path.join(package, '__init__.py')) as init_fd:
        for line in init_fd:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])  # pylint:disable=eval-used

if __name__ == '__main__':

    setup(name=PACKAGE,
          version=get_version(PACKAGE),
          description=('Provides tools for setting up a complete IoT '
                       'dashboard using standards protocols.'),
          long_description=readme('README.md'),
          author='IoT-LAB Team',
          author_email='admin@iot-lab.info',
          url='http://www.iot-lab.info',
          license='BSD',
          keywords="iot demonstration web coap mqtt",
          platforms='any',
          packages=['pyaiot'],
          scripts=[pjoin('bin', 'aiot-broker'),
                   pjoin('bin', 'aiot-coap-gateway'),
                   pjoin('bin', 'aiot-ws-gateway'),
                   pjoin('bin', 'aiot-dashboard')],
          install_requires=[
            'tornado>=4.4.2',
            'aiocoap>=0.2',
            'hbmqtt>=0.8'
          ],
          classifiers=[
            'Development Status :: 4 - Beta',
            'Programming Language :: Python :: 3 :: Only',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Intended Audience :: Developers',
            'Environment :: Console',
            'Topic :: Communications',
            'License :: OSI Approved :: ',
            'License :: OSI Approved :: BSD License'],
          zip_safe=False,
          )
