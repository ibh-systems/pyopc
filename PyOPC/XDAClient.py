#! /usr/bin/env python
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

'''OPC XMLDA 1.0 Client module '''

import string,random

import OpcXmlDaSrv_services as OPCSrv
from OPCContainers import *

def gen_operation(op):
    ''' Generate a OPC operation '''
    
    def operation(self, *IClist, **Options):
        ''' OPC Operation '''

        x = getattr(OPCSrv,op+'SoapIn')()
        
        # Apply General attributes (Options)
        self.fill_tc(x,IClist,Options)

        # All Options should be gone, if not raise error
        if Options:
            raise TypeError('Unknown options given: %s',str(Options))

        # Now actually do the operation
        try:
            result = getattr(self._portType,op)(x)
        except ZSI.FaultException, z:
            raise OPCServerError(*z.fault.args)

        return self.read_tc(result)

    return operation


class XDAClient(OPCOperation):
    ''' Class for accessing OPC XMLDA Servers'''

    # This has to be true as if not set dispatching does not work
    ReturnItemPath = True
    ReturnItemName = True

    # Indicates if Values are returned in Write response messages
    ReturnValuesOnReply = False
    
    def __init__(self,**kwds):

        # Now set object attributes accordings to keywords
        # This may be used to set default values
        for key,value in kwds.items():
            setattr(self,key,value)

        self._loc = OPCSrv.OpcXmlDaSrvLocator()
        # Set address
        self._portType = self._loc.\
                         getOpcXmlDaSrvSoap(self.OPCServerAddress,
                                             tracefile =  file('soap.log','w'))
        
        
        # Build a fancy and unique request handle
        random.seed()
        c = string.letters + string.digits
        s = ''.join([c[random.randint(0,len(c)-1)] for b in range(10)])
        self.ClientRequestHandle = 'ZSI_'+s
    
    # Generate traditional OPC operations
    GetStatus = gen_operation('GetStatus')
    Read = gen_operation('Read')
    Write = gen_operation('Write')
    Subscribe = gen_operation('Subscribe')
    SubscriptionPolledRefresh= gen_operation('SubscriptionPolledRefresh')
    SubscriptionCancel = gen_operation('SubscriptionCancel')
    Browse = gen_operation('Browse')
    GetProperties = gen_operation('GetProperties')
    

    def GetSupportedLocales(self):
        ''' Return a list of all supported Locales on the XMLDA Server '''
        rb,status = self.GetStatus()
        return status.get('SupportedLocaleIDs',[])

    def BrowseTree(self,ItemPath='', ItemName=''):
        ''' Recursively browse tree and pretty print result '''
        # Receipt taken from Python Cookbook Page 159

        el,rb = self.Browse(ItemPath=ItemPath,
                            ItemName=ItemName)

        iterators = [ iter(el) ]

        while iterators:
            # loop on the currently most-nested (last) iterator
            for el in iterators[-1]:
                if el.HasChildren:
                    # subsequence found, go loop on iterator on subsequence
                    yield str(el.ItemName)
                    el,rb = self.Browse(ItemPath=el.ItemPath,
                                        ItemName=el.ItemName)
                    iterators.append(iter(el))
                    break
                else:
                    yield ' '+str(el.ItemName)
            else:
                # most-nested iterator exhausted, go back, loop on its parent
                iterators.pop()


if __name__ == '__main__':
    # Test some functions

    def print_dict(d={}):
        for key,value in d.items():
            print key + '=' + str(value)

    def print_result(param):
        print_dict(param[1])
        for i in param[0]:
            print
            print i
        
    # PyOPC Demo server
    address='http://violin.qwer.tk:8000/'
    
    xda = XDAClient(OPCServerAddress=address)

    # Status
    print_result(xda.GetStatus())
    #print

    
    #print xda.GetSupportedLocales()

    # Build ItemContainer list for various operations
    #icl = [ItemContainer(ItemName='Static.Simple Types.Float', Value=12.2),
    #       ItemContainer(ItemName='Static.Simple Types.Int',Value = 10),
    #       ItemContainer(ItemName='Static.Simple Types.String', Value = 'abc')]

    # Read
    #print_result(xda.Read(icl,MaxAge=1110))
    # Write
    #print_result(xda.Write(icl))
##     print_result(xda.Browse(ItemName='Static.Simple Types',
##                             ReturnAllProperties=False,
##                             PropertyNames=('euType','accessRights')
##                             ))
##     print_result(xda.GetProperties(icl,
##                                    PropertyNames=('euType','accessRights')))
##     i,rd = xda.Subscribe(icl,SubscriptionPingRate=100000)
##     print_result((i,rd))
##     s= rd['ServerSubHandle']
##     print_result(xda.SubscriptionPolledRefresh(ServerSubHandles=s,
##                                                ReturnAllItems=True))
##     print_result(xda.SubscriptionCancel(ServerSubHandle='S3635793'))
