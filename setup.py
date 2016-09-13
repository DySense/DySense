#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from setuptools import setup
from dysense.core.version import app_version

def readme():
    with open('README.md') as f:
        return f.read()

if __name__ == "__main__":
    setup(name='DySense',
          version=app_version,
          description='Dynamic Sensing Program',
          long_description=readme(),
          keywords='data sensors collection',
          url='TODO',
          author='',
          author_email='',
          license='See LICENSE.txt',
          packages=['dysense'],
          install_requires=[
              'pyserial',
			  'pyyaml',
			  'pyzmq',
			  'utm', # for trimble GPS conversions, should get rid of this eventually
              'numpy'
			  #'pyqt4' PyQt needs to be installed separately
          ],
          zip_safe=False)