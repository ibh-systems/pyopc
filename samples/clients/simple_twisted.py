#!/usr/bin/env python
from PyOPC.OPCContainers import *
from PyOPC.TWXDAClient import TWXDAClient
from twisted.internet import reactor

OPERATIONS = 3

def print_options((ilist,options)):
    print ilist; print options; print
    global OPERATIONS
    OPERATIONS -= 1
    if OPERATIONS == 0:
        reactor.stop()

def handleError(failure):
    print "An Error occured"
    print failure.getTraceback()
    reactor.stop()
    
address='http://violin.qwer.tk:8000/'

xda = TWXDAClient(OPCServerAddress=address,
                ReturnErrorText=True)

d = xda.twGetStatus()
d.addCallback(print_options)
d.addErrback(handleError)

d = xda.twBrowse()
d.addCallback(print_options)
d.addErrback(handleError)

d = xda.twRead([ItemContainer(ItemName='simple_item', MaxAge=500)],
               LocaleID='en-us')
d.addCallback(print_options)
d.addErrback(handleError)

reactor.run()
