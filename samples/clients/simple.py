#!/usr/bin/env python
from PyOPC.OPCContainers import *
from PyOPC.XDAClient import XDAClient

def print_options((ilist,options)):
    print ilist; print options; print
    
address='http://violin.qwer.tk:8000/'

xda = XDAClient(OPCServerAddress=address,
                ReturnErrorText=True)

print_options(xda.GetStatus())
print_options(xda.Browse())
print_options(xda.Read([ItemContainer(ItemName='simple_item', MaxAge=500)],
                       LocaleID='en-us'))
