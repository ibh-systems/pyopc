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
'''Basic OPC XML-DA Servers '''
import copy
import twisted
from twisted.internet import reactor,defer
from twisted.python import log

from PyOPC.XDAServer import XDAServer
from PyOPC.XDAServer import ItemPairHolder
from PyOPC.OPCContainers import *

class BasicXDAServer(XDAServer):
    ''' Class that implements a very basic XMLDA OPC Server
    The server accepts every itemname/path and returns a default value '''

    OPCServerAddress = '/'
    SupportedLocaleIDs = ('en-us',)

    # Status specifics
    StatusInfo = 'This is a very basic XMLDA OPC server for testing'

    # All items in "OPCItems" are accessible in the server
    # The format is: ((ItemContainer(),(Properties)),(ItemContainer(),...))
    # The following options can/should be set on the ItemContainer:
    #
    # ValueTypeQualifer
    # Timestamp
    # ResultID, DiagnosticInfo, ErrorText
    # QualityField, LimitField, VendorField
    # ReadDelay, WriteDelay
    # 
    # Properties of any kind can be added to the item
    
    OPCItems = ()

    def __init__(self,*kl,**kd):
        ''' Initialize Test Server '''
        # Predefined Item Values
        self.OPCItemDict = self.mkItems(self.OPCItems)
        super(BasicXDAServer,self).__init__(self,*kl,**kd)

    def mkItems(self,kl):
        ''' Make a dictionary of Items '''
        d = {}
        for item,properties in kl:
            item.addProperties(properties)
            item.IsEmpty = False
            d[mkItemKey(item)] = copy.deepcopy(item)
        return d
   
    ######################### OPC Operations #######################
    def Read(self,(IPH,inOptions,outOptions)):
        ''' Return a dummy value for all read requests '''
        newIPH = ItemPairHolder()
        for inItem, outItem in IPH:
            key = mkItemKey(inItem)
            if self.OPCItemDict.has_key(key):
                newIPH.append(inItem,
                              outItem = copy.deepcopy(self.OPCItemDict[key]))
            else:
                newIPH.append(inItem,
                              ItemContainer(ResultID=\
                                            self.OPC_E_UNKNOWNITEMNAME,
                                            ErrorText=\
                                            'No such OPC Item'))
        return super(BasicXDAServer,self).Read((newIPH,inOptions,outOptions))
        
    def Write(self,(IPH,inOptions,outOptions)):
        ''' Write to the item dictionary '''

        for inItem,outItem in IPH:
            key = mkItemKey(inItem)
            if key and outItem.IsEmpty:
                WriteItem = self.OPCItemDict.get(key,None)
                if not WriteItem:
                    # No such item, create new one
                    WriteItem = ItemContainer()
                    self.OPCItemDict[key] = WriteItem
                # Only write what is not None
                if inItem.Value:
                    WriteItem.Value = inItem.Value
                if inItem.Timestamp:
                    WriteItem.Timestamp = inItem.Timestamp
                else:
                    WriteItem.Timestamp = datetime.datetime.now()
                if inItem.QualityField:
                    WriteItem.QualityField = inItem.QualityField
                if inItem.LimitField:
                    WriteItem.LimitField = inItem.LimitField
                if inItem.VendorField:
                    WriteItem.VendorField = inItem.VendorField
                
        # Call the superclass' write in a deferred style
        # Else possible Reads would be blocking
        d = defer.maybeDeferred(super(BasicXDAServer,self).Write,
                                (IPH,inOptions,outOptions))
        # Add errback, because if not, no tracebacks are displayed
        d.addErrback(log.err)
        return d

    def Browse(self,(IPH,inOptions,outOptions)):
        ''' Create OPC Browse data
        '''
    
        # FIXME this is still ugly
        for key in self.OPCItemDict.keys():
            IPH.append(ItemContainer(),
                       ItemContainer(ItemName=key,
                                     IsItem = True,
                                     HasChildren = False))

        return super(BasicXDAServer,self).Browse((IPH,inOptions,outOptions))
            
    
    def GetProperties(self,(IPH,inOptions,outOptions)):
        ''' Create OPC GetProperties data
        '''
        # Every item has the same property for this test client
        for inItem,outItem in IPH:
            key = mkItemKey(inItem)
            if self.OPCItemDict.has_key(key):
                if inOptions.get('ReturnAllProperties', None):
                    outItem.addProperties(self.OPCItemDict[key].
                                          listProperties())
                else:
                    reqProps = inOptions.get('PropertyNames',None)
                    if reqProps:
                        for prp in self.OPCItemDict[key].listProperties():
                            if prp.Name in reqProps:
                                outItem.addProperty(prp)
        return super(BasicXDAServer,self).GetProperties((IPH,
                                                        inOptions,
                                                        outOptions))

if __name__ == '__main__':
    # Start the basic server
    from twisted.web import resource, server
    xdasrv = BasicXDAServer(http_log_fn = 'http.log')
    root = resource.Resource()
    root.putChild('',xdasrv)
    site = server.Site(root)
    reactor.listenTCP(8000, site)
    reactor.run()
