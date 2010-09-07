#!/usr/bin/python

from setuptools import setup

setup(name='PyOPC',
      version='0.1',
      description="PyOPC is a Python Library implementing the XML - Data Access Protocol Version 1.01",
      long_description="",
      author='Hermann Himmelbauer (dusty128)',
      author_email='',
      license='GPL',
      packages=['PyOPC', 'PyOPC.servers', 'PyOPC.protocols',],
      zip_safe=False,
      install_requires=[],
      )
