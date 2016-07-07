#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from setuptools import setup
from source.version import app_version

def readme():
    with open('README.rst') as f:
        return f.read()

if __name__ == "__main__":
    setup(name='dysense',
          version=app_version,
          description='Dynamic Sensing Program',
          long_description=readme(),
          keywords='data sensors',
          url='TODO',
          author='',
          author_email='',
          license='TODO',
          packages=['source'],
          install_requires=[
              'pyserial',
			  'pyyaml',
			  'pyzmq',
			  'utm' # for trimble GPS conversions
			  #'pyqt4' PyQt needs to be installed separately
          ],
          zip_safe=False)