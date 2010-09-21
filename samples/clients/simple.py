#!/usr/bin/env python
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
from PyOPC.OPCContainers import ItemContainer
from PyOPC.XDAClient import XDAClient

# address='http://violin.qwer.tk:8000/'
address='http://www.advosol.us/xmldademo/xml_sim/OpcXmlDaServer.asmx'

xda = XDAClient(OPCServerAddress=address, ReturnErrorText=True)

print xda.GetStatus()
print xda.Browse()

# hard coded request for http://violin.qwer.tk:8000/.
# xda.Read([ItemContainer(ItemName='simple_item', MaxAge=500)], LocaleID='en-us')

print "querying one item at a time"
requestable = [i for i in xda.Browse()[0] if i.IsItem is True]
for name in [i.ItemName for i in requestable]:
    print xda.Read([ItemContainer(ItemName=name, MaxAge=5000)], LocaleID='en-us')

print "querying all items simultaneously"
print xda.Read(requestable)
