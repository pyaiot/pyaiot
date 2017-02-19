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


def read(fname):
    """Utility function to read the README. Used for long description."""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

if __name__ == '__main__':

    setup(name='iot-kit',
          version='0.1',
          description=('Provides tools for setting up a complete IoT '
                       'dashboard using standards protocols.'),
          long_description=read('README.md'),
          author='IoT-LAB Team',
          author_email='admin@iot-lab.info',
          url='http://www.iot-lab.info',
          license='BSD',
          keywords="iot demonstration web coap mqtt",
          platforms='any',
          packages=['iotkit'],
          scripts=[pjoin('bin', 'iot-broker'),
                   pjoin('bin', 'iot-dashboard')],
          install_requires=[
            'tornado>=4.4.2',
            'aiocoap>=0.2',
            'hbmqtt>=0.8',
          ],
          classifiers=[
            'Programming Language :: Python :: 3 :: Only',
            'Intended Audience :: Developers',
            'Environment :: Console'
            'Topic :: Communications',
            'License :: OSI Approved :: '
            'GNU Lesser General Public License v3 or later (LGPLv3+)', ],
          zip_safe=False,
          )
