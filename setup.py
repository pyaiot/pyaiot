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
          python_requires='>=3.4',
          install_requires=[
            'tornado>=4.4.2',
            'aiocoap>=0.3',
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
