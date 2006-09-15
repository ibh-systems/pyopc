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

    def GetStatus(self,(IPH,inOptions,outOptions)):
        ''' Modifications for testing purposes '''

        # Create exceptions if specific ClientRequestHandles are received
        c = inOptions.get('ClientRequestHandle',None)
        if c == 'ReturnFault1':
            raise OPCServerError(self.OPC_E_BUSY,
                                 'Sorry - The Server is busy by now!')
        if c == 'ReturnFault2':
            # Here is some faulty code that raises an error
            x = 1/0

        return super(TestXDAServer,self).Read((IPH,inOptions,outOptions))


    def Read(self,(IPH,inOptions,outOptions)):
        ''' Read specifics for testing purposes '''
        for inItem, outItem in IPH:
            key = mkItemKey(inItem)
            if self.OPCItemDict.has_key(key):
                self.ReadTestList.append(key)
        return super(TestXDAServer,self).Read((IPH,inOptions,outOptions))
        

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
    def testDeadband(self):
        ''' Test Deadband function '''
        oldItem = ItemContainer()
        newItem = ItemContainer()
        # These should be equal
        self.failIf(self.HasChanged(oldItem,newItem))
        # Now change one attribute
        newItem.QualityField = 'bad'
        self.failUnless(self.HasChanged(oldItem,newItem))

        # Test Integer value change
        oldItem.Value=100
        # Reset
        newItem = copy.copy(oldItem)
        # These should be equal
        self.failIf(self.HasChanged(oldItem,newItem))
        # Now set Deadband = 0
        newItem.Deadband = 0
        self.failIf(self.HasChanged(oldItem,newItem))
        # Now change one attribute
        newItem.Value = 105
        self.failUnless(self.HasChanged(oldItem,newItem))

        # DEADBAND TESTS
        oldItem.Value = None
        # Do all tests with deadband=10.1
        oldItem.Deadband = 10.1
        newItem = copy.copy(oldItem)
        # Integer
        oldItem.Value = 100
        newItem.Value = 110
        self.failIf(self.HasChanged(oldItem,newItem))
        newItem.Value = 111
        self.failUnless(self.HasChanged(oldItem,newItem))
        # Float
        oldItem.Value = 100.0
        newItem.Value = 110.0
        self.failIf(self.HasChanged(oldItem,newItem))
        newItem.Value = 111.0
        self.failUnless(self.HasChanged(oldItem,newItem))

    ###############################################################
    def testFault1(self):
        ''' Test if Server Faults are handled correctly '''
        d=self.xda.twGetStatus(ClientRequestHandle='ReturnFault1')
        d.addCallback(self._cbFault1)
        d.addErrback(self._ebFault1)
        return d
    def _cbFault1(self,(ilist,Options)):
        self.fail("Callback should never be called")
    def _ebFault1(self,failure):
        self.failUnless(failure.check(ZSI.Fault), ZSI.Fault)
        # Now check what kind of error was issued
        self.assertEqual(failure.value.code,self.OPC_E_BUSY)

    def testFault2(self):
        ''' Test if Server Faults are handled correctly '''
        d=self.xda.twGetStatus(ClientRequestHandle='ReturnFault2')
        d.addCallback(self._cbFault2)
        d.addErrback(self._ebFault2)
        return d
    def _cbFault2(self,(ilist,Options)):
        self.fail("Callback should never be called")
    def _ebFault2(self,failure):
        # This should be a ZSI.Fault now
        self.failUnless(failure.check(ZSI.Fault), ZSI.Fault)
        # Now check what kind of error was issued
        self.failUnless('ZeroDivision' in failure.value.detail[0].string)
        

    ###############################################################
    def testCache(self):
        ''' Test if the caching algorithm is working properly
        Stage1: Read items into cache'''
        # Purge the cache so that is empty for sure
        # Initialize a TestList that will be filled by Read commands
        self.xdasrv.ReadTestList = []
        self.xdasrv.ReadCache.flush(0)
        self.assertEqual(len(self.xdasrv.ReadCache._cache),0)
        # Read two arbitrary items so that they are in cache for sure
        d=self.xda.twRead(ItemContainer(ItemName='sample_integer',
                                        ClientItemHandle='woie32'),
                          ItemContainer(ItemName='sample_float',
                                        ClientItemHandle='xyz12'),
                          ItemContainer(ItemName='NotAvailable',
                                        ClientItemHandle='xyz12'),
                          ReturnItemTime=True)
        d.addCallback(self._cbtestCache)

        # Add other stages of the test
        d.addCallback(self._st2_testCache)
        d.addCallback(self._st3_testCache)
        d.addCallback(self._st4_testCache)
        d.addCallback(self._st5_testCache)
        # Return deferred to the trial-unittest
        return d
    def _cbtestCache(self,(ilist,Options)):
        ''' CB-Stage1: Check if items are in cache now '''
        # Cache should have two entries now
        self.assertEqual(len(self.xdasrv.ReadCache._cache),2)
        # Two reads should be logged in ReadTestList
        self.assertEqual(self.xdasrv.ReadTestList,['sample_integer',
                                                   'sample_float'])
    def _st2_testCache(self,result):
        ''' Stage2: Read one item from the cache and another with MaxAge=0 '''
        # Now do one cached and one "real" Item read
        d=self.xda.twRead(ItemContainer(ItemName='sample_integer',
                                        ClientItemHandle='woie32'),
                          ItemContainer(ItemName='sample_float',
                                        ClientItemHandle='xyz12',
                                        MaxAge=0),
                          ReturnItemTime=True)
        d.addCallback(self._cbst2_testCache)
        return d
    def _cbst2_testCache(self,(ilist,Options)):
        ''' CB-Stage2: Check if only one item was read from the cache '''
        # Cache should have two entries now
        self.assertEqual(len(self.xdasrv.ReadCache._cache),2)
        # Three reads should be logged in ReadTestList
        # sample_integer should not be read again as it should be cached
        self.assertEqual(self.xdasrv.ReadTestList,['sample_integer',
                                                   'sample_float',
                                                   'sample_float'])
    def _st3_testCache(self,result):
        ''' Stage3: Do a no-cache read with MaxAge on an OptionLevel '''
        # Now do one cached and one "real" Item read
        d=self.xda.twRead(ItemContainer(ItemName='sample_integer',
                                        ClientItemHandle='woie32'),
                          ItemContainer(ItemName='sample_float',
                                        ClientItemHandle='xyz12'),
                          ReturnItemTime=True,
                          MaxAge=0)
        d.addCallback(self._cbst3_testCache)
        return d
    def _cbst3_testCache(self,(ilist,Options)):
        ''' Stage3: Nothing should be read from the cache '''
        # Cache should have two entries now
        self.assertEqual(len(self.xdasrv.ReadCache._cache),2)
        # Five reads should be logged in ReadTestList
        # All should be read again as it should be cached
        self.assertEqual(self.xdasrv.ReadTestList,['sample_integer',
                                                   'sample_float',
                                                   'sample_float',
                                                   'sample_integer',
                                                   'sample_float'])
    def _st4_testCache(self,result):
        ''' Stage4 Pepare: Write an item '''
        # Now do one cached and one "real" Item read
        d = self.xda.twWrite(ItemContainer(ItemName='sample_integer',
                                       Value=99))
        d.addCallback(self._st4prep_testCache)
        return d
    def _st4prep_testCache(self,result):
        ''' Stage4: Read two items, only one should be cached due to the
        Write operation above. '''
        # Only one item should be cached now, the other should be purged
        self.assertEqual(len(self.xdasrv.ReadCache._cache),1)
        # read items again
        d=self.xda.twRead(ItemContainer(ItemName='sample_integer',
                                        ClientItemHandle='woie32'),
                          ItemContainer(ItemName='sample_float',
                                        ClientItemHandle='xyz12'))
        d.addCallback(self._cbst4_testCache)
        return d
    def _cbst4_testCache(self,(ilist,Options)):
        ''' Stage4: Only one should be read from cache '''
        # Cache should have two entries again
        self.assertEqual(len(self.xdasrv.ReadCache._cache),2)
        # Six reads should be logged in ReadTestList
        # Only sample_integer should be read again
        self.assertEqual(self.xdasrv.ReadTestList,['sample_integer',
                                                   'sample_float',
                                                   'sample_float',
                                                   'sample_integer',
                                                   'sample_float',
                                                   'sample_integer'])
        self.assertEqual(ilist[0].Value,99)
    def _st5_testCache(self,result):
        ''' Stage5: Disable Automatic Item Caching '''
        # Disable caching in the server
        self.xdasrv.AutoItemCache=False
        # Purge the cache so that is empty for sure
        self.xdasrv.ReadCache.flush(0)
        self.assertEqual(len(self.xdasrv.ReadCache._cache),0)
        # read two items
        d=self.xda.twRead(ItemContainer(ItemName='sample_integer'),
                          ItemContainer(ItemName='sample_float'))
        d.addCallback(self._cbst5_testCache)
        return d
    def _cbst5_testCache(self,(ilist,Options)):
        ''' Stage5: Nothing should be cached now '''
        # Cache should have two entries again
        self.assertEqual(len(self.xdasrv.ReadCache._cache),0)
        self.assertEqual(self.xdasrv.ReadTestList,['sample_integer',
                                                   'sample_float',
                                                   'sample_float',
                                                   'sample_integer',
                                                   'sample_float',
                                                   'sample_integer',
                                                   'sample_integer',
                                                   'sample_float'])
        # Enable ItemCaching again for other tests
        self.xdasrv.AutoItemCache=True
        # Clean up everything
        self.xdasrv.ReadTestList = []           
