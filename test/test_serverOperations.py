'''OPC XMLDA Dumb Server '''

import random,copy
import twisted
from twisted.web import resource, server
from twisted.internet import reactor,defer
from twisted.trial import unittest
from twisted.python import log


from PyOPC.XDAServer import XDAServer
from PyOPC.TWXDAClient import TWXDAClient
from PyOPC.OPCContainers import *
from PyOPC.servers.basic import BasicXDAServer

# Read sample OPC items for testing
import sample_items

# Debug delayed calls
twisted.internet.base.DelayedCall.debug = True

class TestXDAServer(BasicXDAServer):
    UTEST = True
    UTEST_DEFERSUB = {}
    # Small buffer, which makes the test easier
    BufferSize = 3

    OPCItems = sample_items.TestOPCItems

    def Write(self,(IPH,inOptions,outOptions)):
        ''' Set a single dummy value from all received items '''
        
        for inItem,outItem in IPH:
            key = mkItemKey(inItem)
            if key:
                if 'notavail' in key.lower():
                    # Generate an error
                    outItem.ResultID=self.OPC_E_UNKNOWNITEMNAME
   
        return super(TestXDAServer,self).Write((IPH,inOptions,outOptions))


class BasicOperations(unittest.TestCase,TestXDAServer):

    def _listen(self, site):
        return reactor.listenTCP(8000, site, interface="127.0.0.1")

    def setUp(self):
        self.xdasrv = TestXDAServer(http_log_fn = 'http.log')
        root = resource.Resource()
        root.putChild('',self.xdasrv)
        site = server.Site(root)
        self.port = self._listen(site)
        reactor.iterate(); reactor.iterate()
        self.portno = self.port.getHost().port
        self.URL = "http://127.0.0.1:%d/" % self.portno
        self.xda = TWXDAClient(OPCServerAddress = self.URL)

    def tearDown(self):
        self.port.stopListening()
        reactor.iterate();reactor.iterate()
        del self.port
        

    ###############################################################
    def testGetStatus(self):
        ''' Test Get Status and Reply Base '''
        d=self.xda.twGetStatus(LocaleID='NotAvailable',
                          ClientRequestHandle='ui293')
        d.addCallback(self._cbGetStatus)
        return d
    def _cbGetStatus(self,(ilist,Options)):
        self.assertEqual(Options.get('ServerState',None),'running')
        self.assertEqual(Options.get('ClientRequestHandle',None),'ui293')
        self.assertEqual(Options.get('RevisedLocaleID',None),'en-us')
        # There has to be a RcvTime and ReplyTime
        self.failUnless(Options.get('RcvTime',None))
        self.failUnless(Options.get('ReplyTime',None))
        self.assertEqual(Options.get('StatusInfo',None), self.StatusInfo)
        self.assertEqual(ilist,[])

    ###############################################################
    def testRead_Data(self):
        ''' Test OPC Read on various data '''
        items = []
        for key,value in self.xdasrv.OPCItemDict.items():
            if 'delay' not in key:
                items.append(value)
        d=self.xda.twRead(items)
        d.addCallback(self._cbtestRead_Data)
        return d
    def _cbtestRead_Data(self,(ilist,Options)):
        for item in ilist:
            self.assertEqual(item.Value,
                             self.xdasrv.OPCItemDict[mkItemKey(item)].Value)

    ###############################################################
    def testRead_RB(self):
        ''' Read OPC Data with all available props in Reply Base '''
        d=self.xda.twRead(ItemContainer(ItemName='sample_integer',
                                        ClientItemHandle='woie32'),
                          ItemContainer(ItemName='NotAvailable',
                                        ClientItemHandle='xyz12'),
                          ReturnErrorText=True,
                          ReturnDiagnosticInfo=True,
                          ReturnItemTime=True,
                          ReturnItemPath=True,
                          ReturnItemName=True)
        d.addCallback(self._cbtestRead_RB)
        return d
    def _cbtestRead_RB(self,(ilist,Options)):
        self.assertEqual(ilist[0].ClientItemHandle,'woie32')
        self.assertEqual(ilist[0].ErrorText,None)
        self.assertEqual(ilist[0].DiagnosticInfo,'')
        self.assertEqual(ilist[0].Timestamp,sample_items.def_ts)
        self.assertEqual(ilist[0].ItemName,'sample_integer')
        # ItemPath should be empty but not None as it is requested
        self.assertEqual(ilist[0].ItemPath,'')
        self.assertEqual(ilist[1].ResultID,OPCBasic.OPC_E_UNKNOWNITEMNAME)
        self.assertEqual(ilist[1].ErrorText,'No such OPC Item')

    ###############################################################
    def testRead_noRB(self):
        ''' Read OPC Data WITHOUT all available props in Reply Base '''
        d=self.xda.twRead(ItemContainer(ItemName='sample_integer',
                                        ClientItemHandle='woie32'),
                          ItemContainer(ItemName='NotAvailable',
                                        ClientItemHandle='xyz12'),
                          ReturnErrorText=False,
                          ReturnDiagnosticInfo=False,
                          ReturnItemTime=False,
                          ReturnItemPath=False,
                          ReturnItemName=False)
        d.addCallback(self._cbtestRead_noRB)
        return d
    def _cbtestRead_noRB(self,(ilist,Options)):
        self.assertEqual(ilist[0].ClientItemHandle,'woie32')
        self.assertEqual(ilist[0].ErrorText,None)
        self.assertEqual(ilist[0].DiagnosticInfo,None)
        self.assertEqual(ilist[0].Timestamp,None)
        self.assertEqual(ilist[0].ItemName,None)
        self.assertEqual(ilist[0].ItemPath,None)
        self.assertEqual(ilist[1].ResultID,OPCBasic.OPC_E_UNKNOWNITEMNAME)
        self.assertEqual(ilist[1].ErrorText,None)
        
    ###############################################################
    def testRead_Unknown(self):
        ''' Read Unknown Item '''
        d=self.xda.twRead(ItemContainer(ItemName='NotAvailable',
                                   ClientItemHandle='woie32'))
        d.addCallback(self._cbtestRead_Unknown)
        return d
    def _cbtestRead_Unknown(self,(ilist,Options)):
        self.assertEqual(ilist[0].ResultID,OPCBasic.OPC_E_UNKNOWNITEMNAME)
        self.assertEqual(ilist[0].ClientItemHandle,'woie32')

    ###############################################################
    def testWrite_NoVal(self):
        ''' Write valid/invalid data, dont readback values '''
        d=self.xda.twWrite(ItemContainer(ItemName='NotAvailable',
                                         ClientItemHandle='woie32',
                                         Value=15),
                           ItemContainer(ItemName='sample_integer',
                                         Value=16),
                           ReturnValuesOnReply=False)
        d.addCallback(self._cbtestWrite_NoVal)
        d.addErrback(log.err)
        return d
    def _cbtestWrite_NoVal(self,(ilist,Options)):
        # Only one item (the failing one) should come back
        self.assertEqual(len(ilist),2)
        self.assertEqual(ilist[0].ClientItemHandle,'woie32')
        self.assertEqual(ilist[0].ResultID[1],
                         OPCBasic.OPC_E_UNKNOWNITEMNAME[1])
        self.assertEqual(ilist[1].Value,None)
        self.assertEqual(ilist[1].ResultID,None)

    ###############################################################
    def testWrite_Val(self):
        ''' Write valid/invalid data, readback values '''
        d=self.xda.twWrite(ItemContainer(ItemName='sample_integer',
                                         Value=18),
                           ItemContainer(ItemName='NotAvailable',
                                         ClientItemHandle='woie32',
                                         Value=15),
                           ItemContainer(ItemName='new_item',
                                         Value='Hello, World'),
                           ReturnValuesOnReply=True)
        d.addCallback(self._cbtestWrite_Val)
        d.addErrback(log.err)
        return d
    def _cbtestWrite_Val(self,(ilist,Options)):
        # Alle items should come back in the right sequence
        self.assertEqual(len(ilist),3)
        self.assertEqual(ilist[0].Value,18)
        self.assertEqual(ilist[1].ClientItemHandle,'woie32')
        self.assertEqual(ilist[1].ResultID[1],
                         OPCBasic.OPC_E_UNKNOWNITEMNAME[1])
        self.assertEqual(ilist[2].Value,'Hello, World')

    ###############################################################
    def testGetProperties1(self):
        ''' Read all available item Properties '''
        d=self.xda.twGetProperties(ItemContainer(ItemName='sample_integer'),
                                   ItemContainer(ItemName='sample_integerRO'),
                                   ItemContainer(ItemName='sample_float'),
                                   PropertyNames=[QName(NS_PYO,'NotAvail'),
                                                  QName(NS_XDA,'accessRights')],
                                   ReturnAllProperties=True)
        d.addCallback(self._cbtestGetProperties1)
        return d
    def _cbtestGetProperties1(self,(ilist,Options)):
        p_accessRights = ilist[0].getProperty('accessRights')
        self.failIf(p_accessRights == None)
        self.assertEqual(p_accessRights.ItemPath,None)
        self.assertEqual(p_accessRights.ItemName,
                         'sample_integer.Property_accessRights')
        p_description = ilist[0].getProperty('description')
        self.failIf(p_description == None)
        p_MyProperty = ilist[0].getProperty('MyProperty')
        self.failIf(p_MyProperty == None)
        self.assertEqual(p_MyProperty.ItemPath,'MyPath')
        self.assertEqual(p_MyProperty.ItemName,'MyName')
        p_value = ilist[0].getProperty('value')
        self.failIf(p_value == None)
        p_quality = ilist[0].getProperty('quality')
        self.failIf(p_quality == None)
        p_timestamp = ilist[0].getProperty('timestamp')
        self.failIf(p_timestamp == None)
        p_scanRate = ilist[0].getProperty('scanRate')
        self.failIf(p_scanRate == None)
        # There should be no values
        for prop in ilist[0].listProperties():
            self.assertEqual(prop.Value, None)
        # So all in all it should be seven Properties
        self.assertEqual(len(ilist[0].listProperties()),7)
        ##### The same for the second item
        p_accessRights = ilist[1].getProperty('accessRights')
        self.failIf(p_accessRights == None)
        self.assertEqual(p_accessRights.ItemPath,None)
        self.assertEqual(p_accessRights.ItemName,
                         'sample_integerRO.Property_accessRights')
        p_description = ilist[1].getProperty('description')
        self.failIf(p_description == None)
        p_MyProperty1 = ilist[1].getProperty('MyProperty1')
        self.failIf(p_MyProperty1 == None)
        self.assertEqual(p_MyProperty1.ItemPath,'MyPath')
        self.assertEqual(p_MyProperty1.ItemName,'MyName')
        p_value = ilist[1].getProperty('value')
        self.failIf(p_value == None)
        p_quality = ilist[1].getProperty('quality')
        self.failIf(p_quality == None)
        p_timestamp = ilist[1].getProperty('timestamp')
        self.failIf(p_timestamp == None)
        p_scanRate = ilist[1].getProperty('scanRate')
        self.failIf(p_scanRate == None)
        # There should be no values
        for prop in ilist[1].listProperties():
            self.assertEqual(prop.Value, None)
        # So all in all it should be seven Properties
        self.assertEqual(len(ilist[1].listProperties()),7)
        # Check Properties for the third item
        self.assertEqual(len(ilist[2].listProperties()),4)


    def testGetProperties2(self):
        ''' Read specific item Properties '''
        d=self.xda.twGetProperties(ItemContainer(ItemName='sample_integer'),
                                   ItemContainer(ItemName='sample_float'),
                                   PropertyNames=[QName(NS_PYO,'NotAvail'),
                                                  QName(NS_XDA,'accessRights')])
        d.addCallback(self._cbtestGetProperties2)
        return d
    def _cbtestGetProperties2(self,(ilist,Options)):
        p_accessRights = ilist[0].getProperty('accessRights')
        self.failIf(p_accessRights == None)
        p_NotAvail = ilist[0].getProperty('NotAvail')
        self.assertEqual(p_NotAvail.ResultID,self.OPC_E_INVALIDPID)
        p_accessRights = ilist[1].getProperty('accessRights')
        self.assertEqual(p_NotAvail.ResultID,self.OPC_E_INVALIDPID)
        p_NotAvail = ilist[1].getProperty('NotAvail')
        self.assertEqual(p_NotAvail.ResultID,self.OPC_E_INVALIDPID)
        

    def testGetProperties3(self):
        ''' Read item Properties with values '''
        d=self.xda.twGetProperties(ItemContainer(ItemName='sample_integer'),
                                   ItemContainer(ItemName='sample_float'),
                                   ReturnAllProperties = True,
                                   ReturnPropertyValues = True)
        d.addCallback(self._cbtestGetProperties3)
        return d
    def _cbtestGetProperties3(self,(ilist,Options)):
        p_accessRights = ilist[0].getProperty('accessRights')
        self.failIf(p_accessRights == None)
        self.assertEqual(p_accessRights.ItemPath,None)
        self.assertEqual(p_accessRights.ItemName,
                         'sample_integer.Property_accessRights')
        p_description = ilist[0].getProperty('description')
        self.failIf(p_description == None)
        p_MyProperty = ilist[0].getProperty('MyProperty')
        self.failIf(p_MyProperty == None)
        self.assertEqual(p_MyProperty.ItemPath,'MyPath')
        self.assertEqual(p_MyProperty.ItemName,'MyName')
        p_value = ilist[0].getProperty('value')
        self.assertEqual(p_value.Value,14)
        p_quality = ilist[0].getProperty('quality')
        self.assertEqual(p_quality.Value,'good')
        p_timestamp = ilist[0].getProperty('timestamp')
        self.failIf(p_timestamp.Value == None)
        p_scanRate = ilist[0].getProperty('scanRate')
        self.assertEqual(p_scanRate.Value,100)
        # So all in all it should be seven Properties
        self.assertEqual(len(ilist[0].listProperties()),7)


    def testBrowse1(self):
        ''' Browse the root object '''
        d=self.xda.twBrowse()
        d.addCallback(self._cbtestBrowse1)
        return d
    def _cbtestBrowse1(self,(ilist,Options)):
        self.assertEqual(len(self.xdasrv.OPCItemDict),len(ilist))

    def testBrowse2(self):
        ''' Browse the root object '''
        d=self.xda.twBrowse(ReturnAllProperties=True,
                            ReturnPropertyValues=False)
        d.addCallback(self._cbtestBrowse2)
        return d
    def _cbtestBrowse2(self,(ilist,Options)):
        self.assertEqual(len(self.xdasrv.OPCItemDict),len(ilist))

    #del testGetStatus
    #del testRead_Data
    #del testRead_RB
    #del testRead_noRB
    #del testRead_Unknown
    #del testWrite_NoVal
    #del testWrite_Val
    #del testGetProperties1
    #del testGetProperties2
    #del testGetProperties3
    #del testBrowse1
    #del testBrowse2
