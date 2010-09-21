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
