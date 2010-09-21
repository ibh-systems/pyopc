#!/usr/bin/python
# This file is part of pyopc.
#
# pyopc is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# pyopc is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General
# Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with pyopc.  If not, see
# <http://www.gnu.org/licenses/>.
#
# $Id$
#

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
