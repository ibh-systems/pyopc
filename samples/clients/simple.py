#!/usr/bin/env python
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
