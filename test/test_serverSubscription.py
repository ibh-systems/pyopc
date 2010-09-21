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

    ######################### Supporting Test Functions
        
    def initSubscriptionTests(self):
        ''' Do some initialization before Subscription Tests '''
        self.TestServerSubHandles = []
        self.Test_dkey_ssh_dict = {}
        self.TestDeferreds = []
        self.xdasrv.UTEST_MSGS = []
        self.xdasrv.UTEST_SUBMSGS = {}
        self.SubOptionsDict = {}
        d = defer.Deferred()
        d.callback(None)
        return d

    def delayWrite(self,delay,*IClist,**Options):
        ''' Write given item, works only with a subscription beforehand'''
        d = defer.Deferred()
        d.addCallback(self.write)
        reactor.callLater(delay,d.callback,(IClist,Options))
        self.TestDeferreds.append(d)
    def write(self,(IClist,Options)):
        ds =  self.xda.twWrite(*IClist,**Options)
        ds.addCallback(self._cbwrite)
        return ds
    def _cbwrite(self,(ilist,Options)):
        # Simple check if write succeeded
        self.failIf(len(ilist) == 0)

    def mkWrite(self,dummy,*IClist,**Options):
        ''' Write given item, ignore results '''
        ds =  self.xda.twWrite(*IClist,**Options)
        ds.addCallback(self._cbmkWrite)
        return ds
    def _cbmkWrite(self,(ilist,Options)):
        # Simple check if write succeeded
        self.failIf(len(ilist) == 0)

    def mkSPR(self,ExpectedWaitTime,HasValue,*IClist,**Options):
        ''' Write given item, works only with a subscription beforehand'''
        d = self.xda.twSubscriptionPolledRefresh(*IClist,**Options)
        d.addCallback(self._cbmkSPR,ExpectedWaitTime,HasValue)
        return d
    def _cbmkSPR(self,(ilist,Options),ExpectedWaitTime,HasValue):
        # Simple check if write succeeded
        if HasValue:
            self.failIf(len(ilist) == 0)
        else:
            self.failUnless(len(ilist) == 0)
        t = self.WriteDelayTime + ExpectedWaitTime
        # Must not be triggered before expected callback
        self.failIf(time.time() < t)
        # Should also not be triggered much later (2 seconds)
        self.failIf(time.time() > (t+2))

    def mkSubscription(self,d,*IClist,**Options):
        ''' Subscribe to an item '''
        # Make unique key for defer dictionary
        dkey = 'SUBDEFER_%s_%s' % (str(time.time()),
                                   random.randint(10000,99999))
        UD = defer.Deferred()
        UD.addCallback(self._CleanupmkSubscription)
        UD.addErrback(log.err)
        self.TestDeferreds.append(UD)
        self.xdasrv.UTEST_DEFERSUB[dkey] = UD
        # Set ClientRequestHandle -> this will be used for callback
        # in the unsubscription
        Options['ClientRequestHandle'] = dkey
        # Store the SubscriptionList and the Options
        self.SubOptionsDict[dkey] = (IClist,Options)
        d.addCallback(self.subscribe,(IClist,Options,dkey))
    def _cbmkSubscription(self,(ilist,Options),dkey):
        # All items should have come back from the Subscription
        #self.assertEqual(len(ilist),1)
        # Record ServerSubHandle for further SPR's
        SSH = Options.get('ServerSubHandle',None)
        if SSH:
            self.TestServerSubHandles.append(SSH)
            self.Test_dkey_ssh_dict[dkey] = SSH
        # ilist/Options used for subscription
        sub_items,inOptions = self.SubOptionsDict[dkey]
        # Check if errors are returned
        if inOptions.get('ReturnValuesOnReply',None) == True:
            self.assertEqual(len(sub_items),len(ilist))
            # All items should be returned in order
            for i,o in zip(sub_items,ilist):
                if i.ItemName.lower().find('notavail') > 0:
                    # Errorneous item
                    self.failIf(o.ResultID == None)
                else:
                    # Returned item should be o.k., check value
                    self.assertEqual(o.Value,
                                     self.xdasrv.\
                                     OPCItemDict[mkItemKey(i)].Value)
        else:
            # Return only errorneous items
            err_items = []
            for item in sub_items:
                if item.ItemName.lower().find('notavail') > 0:
                    err_items.append(item)
            self.assertEqual(len(err_items),len(ilist))
            for item in err_items:
                self.failIf(item.ResultID == None)
    def _CleanupmkSubscription(self,dkey):
        ''' Do some cleanup checks '''
        self.assertEqual(dkey.find('SUBDEFER_'),0)
        # My subscription should be gone now
        self.assertEqual(self.xdasrv.UTEST_DEFERSUB.get(dkey,None),
                         None)
        # ServerSubHandle
        ssh=self.Test_dkey_ssh_dict.get(dkey,None)
        # Subscription specific message list
        sm=self.xdasrv.UTEST_SUBMSGS.get(ssh,None)
        # Do some simple checks
        self.assertEqual(sm[0][1],'addSub')
        self.assertEqual(sm[1][1],'LoopStart')
        self.assertEqual(sm[-1][1],'SubscriptionCancel')
    def subscribe(self,dummy,(IClist,Options,dkey)):
        ds =  self.xda.twSubscribe(*IClist,**Options)
        ds.addCallback(self._cbmkSubscription,dkey)
        return ds

    ###############################################################
    def testSubscribe_NoVal(self):
        ''' Subscribe to Items, dont return values, check loop '''
        UD = defer.Deferred()
        UD.addCallback(self._cbtestSubscribe_NoVal_Cleanup)
        # Add default errback
        UD.addErrback(log.err)
        self.xdasrv.UTEST_DEFERSUB['SUB_DEFERSUB'] = UD
        self.xdasrv.UTEST_MSGS = []
        self.xdasrv.UTEST_SUBMSGS = {}
        d=self.xda.twSubscribe(ItemContainer(ItemName='NotAvail'),
                               ItemContainer(ItemName='sample_integer'),
                               ItemContainer(ItemName='sample_float',
                                             RequestedSamplingRate=700),
                               ReturnValuesOnReply=False,
                               RequestedSamplingRate=600,
                               SubscriptionPingRate=1000,
                               ClientRequestHandle='SUB_DEFERSUB')
        d.addCallback(self._cbtestSubscribe_NoVal)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults([d,UD])
    def _cbtestSubscribe_NoVal(self,(ilist,Options)):
        self.assertEqual(len(ilist),1)
        self.assertEqual(ilist[0].ResultID,
                         OPCBasic.OPC_E_UNKNOWNITEMNAME)
    def _cbtestSubscribe_NoVal_Cleanup(self,result):
        ''' Check if loop runs properly '''
        u=self.xdasrv.UTEST_MSGS
        # The LoopStart of the first item
        self.assertEqual(u[0][1],'LoopStart')
        # Check Sampling rate
        self.assertEqual(u[0][2]*1000,600)
        # The LoopStart of the second item
        self.assertEqual(u[1][1],'LoopStart')
        # Check Sampling rate
        self.assertEqual(u[1][2]*1000,700)
        # Next must be first LoopingRead
        self.assertEqual(u[2][1],'LoopingRead')
        # LoopingRead must not occur before SamplingRate
        self.failIf(1000*(u[2][0]-u[0][0]) < 600)
        # Next must be second LoopingRead
        self.assertEqual(u[3][1],'LoopingRead')
        # LoopingRead must not occur before SamplingRate
        self.failIf(1000*(u[3][0]-u[0][0]) < 700)
        # Next must be SubscriptionCancel
        self.assertEqual(u[4][1],'SubscriptionCancel')
        # SubscriptionCancel must not occur before PingRate
        self.failIf(1000*(u[4][0]-u[0][0]) < 1000)
        # All Subscriptions must be cancelled now
        self.assertEqual(self.xdasrv.SubscriptionDict,{})

    ###############################################################
    def testSubscribe_Val(self):
        ''' Subscribe to Items, return values '''
        UD = defer.Deferred()
        UD.addCallback(self._cbtestSubscribe_Val_Cleanup)
        # Add default errback
        UD.addErrback(log.err)
        self.xdasrv.UTEST_DEFERSUB['SUB_DEFERSUB'] = UD
        self.xdasrv.UTEST_MSGS = []
        self.xdasrv.UTEST_SUBMSGS = {}
        d=self.xda.twSubscribe(ItemContainer(ItemName='NotAvail'),
                               ItemContainer(ItemName='sample_integer'),
                               ItemContainer(ItemName='sample_float'),
                               ReturnValuesOnReply=True,
                               RequestedSamplingRate=60,
                               SubscriptionPingRate=500,
                               ClientRequestHandle='SUB_DEFERSUB')
        d.addCallback(self._cbtestSubscribe_Val)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults([d,UD])
    def _cbtestSubscribe_Val(self,(ilist,Options)):
        # ServerSubhandle has to be there
        self.failUnless('SSubHandle_' in Options.get('ServerSubHandle',None))
        self.assertEqual(len(ilist),3)
        self.assertEqual(ilist[0].ResultID,
                         OPCBasic.OPC_E_UNKNOWNITEMNAME)
        self.assertEqual(ilist[1].Value,14)
        self.assertEqual(ilist[2].Value,96.43)
    def _cbtestSubscribe_Val_Cleanup(self,result):
        ''' Check if loop runs properly '''
        u=self.xdasrv.UTEST_MSGS
        # First must be LoopStart
        self.assertEqual(u[0][1],'LoopStart')
        # Check Sampling rate - should be revised
        self.assertEqual(u[0][2]*1000,100)
        # All Subscriptions must be cancelled now
        self.assertEqual(self.xdasrv.SubscriptionDict,{})


    ###############################################################
    def testSubscribe_Errorneous(self):
        ''' Subscribe only to errorneous Items '''
        self.xdasrv.UTEST_MSGS = []
        self.xdasrv.UTEST_SUBMSGS = {}
        d=self.xda.twSubscribe(ItemContainer(ItemName='NotAvail'))
        d.addCallback(self._cbtestSubscribe_Errorneous)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbtestSubscribe_Errorneous(self,(ilist,Options)):
        # ServerSubhandle has to be there
        self.assertEqual(len(ilist),1)
        self.assertEqual(Options.get('ServerSubHandle',None),None)

    ######################################################################
    def testMultiSubscriptions(self):
        ''' Subscribe to multiple Subscriptions '''
        d = self.initSubscriptionTests()
        # Subscribe to 20 items with a PingRate of 1000
        # This should lead to overlapping subscribes/unsubscribes on
        # slower machines
        for i in range(20):
            self.mkSubscription(d,
                                ItemContainer(ItemName='sample_integer',
                                              RequestedSamplingRate=180),
                                ReturnValuesOnReply=True,
                                SubscriptionPingRate=1000)
        d.addErrback(log.err)
        # FIXME - test that multiple subscriptions on the same items
        #         take advantage of MaxAge=SamplingRate-1ms and Caching
        return defer.gatherResults(self.TestDeferreds)

    ######################################################################
    def testSubscriptionCancel(self):
        ''' Subscribe to Item and Test SubscriptionCancel '''
        UD = defer.Deferred()
        UD.addCallback(self._cbtestSubscriptionCancel_Cleanup)
        # Add default errback
        UD.addErrback(log.err)
        self.xdasrv.UTEST_DEFERSUB['SUB_DEFERSUB'] = UD
        self.xdasrv.UTEST_MSGS = []
        self.xdasrv.UTEST_SUBMSGS = {}
        d=self.xda.twSubscribe(ItemContainer(ItemName='sample_integer'),
                               ReturnValuesOnReply=True,
                               RequestedSamplingRate=1000,
                               SubscriptionPingRate=100000000000000,
                               ClientRequestHandle='SUB_DEFERSUB')
        d.addCallback(self._cbtestSubscriptionCancel)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults([d,UD])
    def _cbtestSubscriptionCancel(self,(ilist,Options)):
        # Now cancel the subscription
        subdict_freeze = dict(self.xdasrv.SubscriptionDict)
        d=self.xda.twSubscriptionCancel(ServerSubHandle=\
                                        Options['ServerSubHandle'],
                                        ClientRequestHandle='SUB_DEFERSUB')
        # Before the cancel, the SubscriptionDict has to have one entry
        self.assertEqual(len(subdict_freeze),1)
        return d
    def _cbtestSubscriptionCancel_Cleanup(self,result):
        ''' Check if loop runs properly '''
        u=self.xdasrv.UTEST_MSGS
        # First must be LoopStart
        self.assertEqual(u[0][1],'LoopStart')
        # Next should be the Subscription Cancel
        self.assertEqual(u[1][1],'SubscriptionCancel')
        # All Subscriptions must be cancelled now
        self.assertEqual(self.xdasrv.SubscriptionDict,{})

    ###############################################################
    def testSPR1_Invalid(self):
        ''' Initiate a SubPolledRefresh with invalid SSHandles '''
        self.InvalidHandles = ['NotValid1','Invalid2'] 
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.InvalidHandles)
        d.addCallback(self._cbtestSPR1_Invalid)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbtestSPR1_Invalid(self,(ilist,Options)):
        # Check that all serversubhandles were invalid
        self.assertEqual(self.InvalidHandles,
                         Options.get('InvalidServerSubHandles',None))

    ###############################################################
    def testSPR2_NoInitValChange(self):
        ''' SPR with Sub with ReturnValuesOnReply=True
        1) Subscribe to an item
        2) A SPR should not return any changed values
        3) Write to this item
        4) A SPR (with HoldTime) should report this change
        5) A SPR (with HoldTime)should not return any further changed values'''

        d = self.initSubscriptionTests()
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_integer'),
                            ReturnValuesOnReply=True,
                            RequestedSamplingRate=100,
                            SubscriptionPingRate=1000)
        d.addCallback(self._st2_testSPR2_NoInitValChange)
        d.addCallback(self._st3_testSPR2_NoInitValChange)
        d.addCallback(self._st4_testSPR2_NoInitValChange)
        d.addCallback(self._st5_testSPR2_NoInitValChange)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults(self.TestDeferreds)
    def _st2_testSPR2_NoInitValChange(self,result):
        # Now do the SPR
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0])
        d.addCallback(self._cbst2_testSPR2_NoInitValChange)
        return d
    def _cbst2_testSPR2_NoInitValChange(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # No values should have changed by now
        self.assertEqual(ilist,[])
        # The Auto-Unsubscribe should be active again
        s=self.xdasrv.SubscriptionDict[self.TestServerSubHandles[0]]
        self.failUnless(s.ClCmdID.active())
    def _st3_testSPR2_NoInitValChange(self,result):
        ''' Now write the item '''
        d=self.xda.twWrite(ItemContainer(ItemName='sample_integer',
                                         Value=24))
        d.addCallback(self._cbst3_testSPR2_NoInitValChangeself)
        return d
    def _cbst3_testSPR2_NoInitValChangeself(self,(ilist,Options)):
        # All items should come back in the right sequence
        self.assertEqual(len(ilist),1)
    def _st4_testSPR2_NoInitValChange(self,result):
        ''' Now do another SPR (with HoldTime (1second)) '''
        # Now do the SPR
        # Mark current time
        self.PollStartTime = time.time()
        s=self.xdasrv.SubscriptionDict[self.TestServerSubHandles[0]]
        self.SubCancelTime = s.ClCmdID.getTime()
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0],
            HoldTime=datetime.datetime.now() + datetime.timedelta(0,2))
        d.addCallback(self._cbst4_testSPR2_NoInitValChange)
        # Add default errback
        return d
    def _cbst4_testSPR2_NoInitValChange(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # A minimum of 1 seconds should have been elapsed
        # FIXME Never two seconds, as the microseconds are cut off due to
        # the ZSI limitation
        self.failIf((time.time() - self.PollStartTime) < 1)
        # One item should have been changed by now
        self.assertEqual(ilist[0].Value,24)
        # The Auto-Unsubscribe should be active again
        s=self.xdasrv.SubscriptionDict[self.TestServerSubHandles[0]]
        self.failUnless(s.ClCmdID.active())
        # Check that the auto-cancel was correctly postponed
        self.failIf((s.ClCmdID.getTime() - self.SubCancelTime) < 1)
    def _st5_testSPR2_NoInitValChange(self,result):
        ''' Now do another SPR (with HoldTime (1second)) '''
        # Now do the SPR
        # Mark current time
        self.PollStartTime = time.time()
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0],
            HoldTime=datetime.datetime.now() + datetime.timedelta(0,2))
        d.addCallback(self._cbst5_testSPR2_NoInitValChange)
        # Add default errback
        return d
    def _cbst5_testSPR2_NoInitValChange(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # A minimum of 1 seconds should have been elapsed
        # FIXME Never two seconds, as the microseconds are cut off due to
        # the ZSI limitation
        self.failIf((time.time() - self.PollStartTime) < 1)
        # No more item should have changed by now
        self.assertEqual(ilist,[])
        # The Auto-Unsubscribe should be active again
        s=self.xdasrv.SubscriptionDict[self.TestServerSubHandles[0]]
        self.failUnless(s.ClCmdID.active())
    def _cbtestSPR2_SubCleanUp(self,result):
        ''' Do some cleanup checks '''
        # All Subscriptions must be cancelled now
        self.assertEqual(self.xdasrv.SubscriptionDict,{})
        
    ############################################################
    def testSPR3_InitValChange(self):
        ''' SPR with Sub with ReturnValuesOnReply=False '''
        d = self.initSubscriptionTests()
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_integer'),
                            ReturnValuesOnReply=False,
                            RequestedSamplingRate=100,
                            SubscriptionPingRate=1000)
        d.addCallback(self._st2_testSPR3_InitValChange)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults(self.TestDeferreds)
    def _st2_testSPR3_InitValChange(self,result):
        # Now do the SPR
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0])
        d.addCallback(self._cbst2_testSPR3_InitValChange)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbst2_testSPR3_InitValChange(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # The value were never read back, hence they are "changed"
        self.assertEqual(ilist[0].Value,14)
    def _cbtestSPR3_SubCleanUp(self,result):
        ''' Do some cleanup checks '''
        # All Subscriptions must be cancelled now
        self.assertEqual(self.xdasrv.SubscriptionDict,{})

    ######################################################################
    def testSPR4_WaitTime(self):
        ''' Test SPR with WaitTime '''
        d = self.initSubscriptionTests()
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_integer',
                                          RequestedSamplingRate=100),
                            ItemContainer(ItemName='sample_float',
                                          RequestedSamplingRate=100),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=1000)
        d.addCallback(self._st2_testSPR4_WaitTime)
        d.addCallback(self._st3_testSPR4_WaitTime)
        d.addCallback(self._st4_testSPR4_WaitTime)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults(self.TestDeferreds)
    def _cbtestSPR4_WaitTime(self,(ilist,Options)):
        # All items should have come back from the Subscription
        self.assertEqual(len(ilist),2)
        # Record ServerSubHandle for further SPR's
        self.TestServerSubHandles[0] =  Options['ServerSubHandle']
    def _st2_testSPR4_WaitTime(self,result):
        ''' Now write one item '''
        d=self.xda.twWrite(ItemContainer(ItemName='sample_float',
                                         Value=26.3),
                           ItemContainer(ItemName='sample_integer',
                                         Value=87))
        d.addCallback(self._cbst2_testSPR4_WaitTime)
        return d
    def _cbst2_testSPR4_WaitTime(self,(ilist,Options)):
        # One (empty) item should come back
        self.assertEqual(len(ilist),2)
    def _st3_testSPR4_WaitTime(self,result):
        ''' Do a Poll with HoldTime=2sec, WaitTime=5sec '''
        self.PollStartTime = time.time()
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0],
            HoldTime=datetime.datetime.now() + datetime.timedelta(0,2),
            WaitTime=5000)
        d.addCallback(self._cbst3_testSPR4_WaitTime)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbst3_testSPR4_WaitTime(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # The value should have changed due to the write above
        self.assertEqual(ilist[0].Value,87)
        self.assertEqual(ilist[1].Value,26.3)
        # check that it came back immediately not before HoldTime
        self.failIf((time.time() - self.PollStartTime) < 1)
        # Check that it came back before WaitTime expired
        self.failIf((time.time() - self.PollStartTime) > 4)
    def _st4_testSPR4_WaitTime(self,result):
        ''' Do a Poll with HoldTime=2sec, WaitTime=2sec, no value change
        Function should come back after the wait expired '''
        self.PollStartTime = time.time()
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0],
            HoldTime=datetime.datetime.now() + datetime.timedelta(0,2),
            WaitTime=2000,
            )
        d.addCallback(self._cbst4_testSPR4_WaitTime)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbst4_testSPR4_WaitTime(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # The value should have changed due to the write above
        self.assertEqual(ilist,[])
        # check that it came back immediately not before HoldTime+WaitTime
        self.failIf((time.time() - self.PollStartTime) < 3)
    def _cbtestSPR4_SubCleanUp(self,result):
        ''' Do some cleanup checks '''
        # All Subscriptions must be cancelled now
        self.assertEqual(self.xdasrv.SubscriptionDict,{})
        

    ######################################################################
    def testSPR5_WaitTime1(self):
        ''' Further SPR with WaitTime test with ReturnAllItems=True '''
        d = self.initSubscriptionTests()
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_float',
                                          RequestedSamplingRate=100),
                            ItemContainer(ItemName='sample_integer',
                                          RequestedSamplingRate=100),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=1000)
        d.addCallback(self._st2_testSPR5_WaitTime1)
        d.addCallback(self._st3_testSPR5_WaitTime1)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults(self.TestDeferreds)
    def _st2_testSPR5_WaitTime1(self,result):
        ''' Do a Poll with HoldTime=2sec, WaitTime=5sec, ReturnAllItems '''
        self.PollStartTime = time.time()
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0],
            HoldTime=datetime.datetime.now() + datetime.timedelta(0,2),
            WaitTime=5000,
            ReturnAllItems = True)
        d.addCallback(self._cbst2_testSPR5_WaitTime1)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbst2_testSPR5_WaitTime1(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # The value should have changed due to the write above
        self.assertEqual(len(ilist),2)
        # check that it came back immediately not before HoldTime
        self.failIf((time.time() - self.PollStartTime) < 1)
        # Check that it came back before WaitTime expired
        self.failIf((time.time() - self.PollStartTime) > 3)
    def _st3_testSPR5_WaitTime1(self,result):
        ''' Do a Poll with HoldTime=2sec, WaitTime=1sec, ReturnAllItems '''
        self.PollStartTime = time.time()
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0],
            HoldTime=datetime.datetime.now() + datetime.timedelta(0,2),
            WaitTime=1000,
            ReturnAllItems = False)
        d.addCallback(self._cbst3_testSPR5_WaitTime1)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbst3_testSPR5_WaitTime1(self,(ilist,Options)):
        # No values have changed, waitTime should expire
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # The value should have changed due to the write above
        self.assertEqual(len(ilist),0)
        # check that it came back immediately not before HoldTime
        self.failIf((time.time() - self.PollStartTime) < 1)
        # Check that it came back after WaitTime expired
        self.failIf((time.time() - self.PollStartTime) < 2)

    ######################################################################
    def testSPR6_WaitTime2(self):
        ''' Check correct callback of SPR during WaitTime '''
        d = self.initSubscriptionTests()
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_integer',
                                          RequestedSamplingRate=180),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=1000)
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_float',
                                          RequestedSamplingRate=190),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=1000)
        self.WriteDelayTime = time.time()
        # This should not trigger a callback
        self.delayWrite(2,
                        ItemContainer(ItemName='sample_integer',
                                      Value=14))
        # This should trigger the callback
        self.delayWrite(3,
                        ItemContainer(ItemName='sample_integer',
                                      Value=87))
        d.addCallback(self._st3_testSPR6_WaitTime2)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults(self.TestDeferreds)
    def _st3_testSPR6_WaitTime2(self,result):
        ''' Do a Poll with HoldTime=2sec, WaitTime=5sec '''
        self.PollStartTime = time.time()
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=[self.TestServerSubHandles[0],
                              self.TestServerSubHandles[1]],
            HoldTime=datetime.datetime.now() + datetime.timedelta(0,2),
            WaitTime=7000)
        d.addCallback(self._cbst3_testSPR6_WaitTime2)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbst3_testSPR6_WaitTime2(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # The value should have changed due to the write above
        self.assertEqual(len(ilist),1)
        self.assertEqual(ilist[0].Value,87)
        # check that it came back not before second Write
        self.failIf((time.time() - self.WriteDelayTime) < 3)
        # Check that it came back before WaitTime expired
        self.failIf((time.time() - self.PollStartTime) > 4)


    ######################################################################
    def testSPR6_WaitTime3(self):
        ''' Check WaitCallback: 5 Subscriptions, 4 Polls '''
        d = self.initSubscriptionTests()
        # 0 - Subscription on sample_string
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_string',
                                          RequestedSamplingRate=181),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=3000)
        # 1 - Subscription on sample_integer
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_integer',
                                          RequestedSamplingRate=182),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=3000)
        # 2 - Subscription on sample_int
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_integer',
                                          RequestedSamplingRate=182),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=3000)
        # 3 - Subscription on sample_int
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_float',
                                          RequestedSamplingRate=182),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=3000)
        # 4 - Subscription on sample_integer
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_integer',
                                          RequestedSamplingRate=183),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=3000)
        # Dummy Subscription, no poll, should die after 0.5 second
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_string',
                                          RequestedSamplingRate=2000),
                            ReturnValuesOnReply=True,
                            SubscriptionPingRate=1000)
        self.WriteDelayTime = time.time()
        # Write to sample_string
        self.delayWrite(5,
                        ItemContainer(ItemName='sample_string',
                                      Value='Call it back!'))
        self.delayWrite(1,
                        ItemContainer(ItemName='sample_float',
                                      Value=11.3))
        self.delayWrite(3,
                        ItemContainer(ItemName='sample_integer',
                                      Value=92))
        d.addCallback(self._st2_testSPR6_WaitTime3)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults(self.TestDeferreds)
    def _st2_testSPR6_WaitTime3(self,result):
        ''' Do a Poll with HoldTime=2sec, WaitTime=5sec '''
        self.PollStartTime = time.time()
        dl = []
        dl.append(self.mkSPR(5,           # Expected Callback time
                             True,        # Should return value
                             ServerSubHandles=[self.TestServerSubHandles[0]],
                             HoldTime=datetime.datetime.now() + \
                             datetime.timedelta(0,2),
                             WaitTime=7000))
        dl.append(self.mkSPR(3,           # Expected Callback time
                             True,        # Should return value
                             ServerSubHandles=[self.TestServerSubHandles[1]],
                             HoldTime=datetime.datetime.now() + \
                             datetime.timedelta(0,2),
                             WaitTime=7000))
        dl.append(self.mkSPR(1,           # Expected Callback time
                             True,        # Should return value
                             ServerSubHandles=[self.TestServerSubHandles[2],
                                               self.TestServerSubHandles[3]],
                             HoldTime=datetime.datetime.now() + \
                             datetime.timedelta(0,2),
                             WaitTime=7000))
        dl.append(self.mkSPR(3,           # Expected Callback time
                             True,        # Should return value
                             ServerSubHandles=[self.TestServerSubHandles[4]],
                             HoldTime=datetime.datetime.now() + \
                             datetime.timedelta(0,2),
                             WaitTime=7000))


        return defer.gatherResults(dl)

    ############################################################
    def testSPR7_Buffering1(self):
        ''' Test Buffering without overflow '''
        d = self.initSubscriptionTests()
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_integer'),
                            ReturnValuesOnReply=True,
                            RequestedSamplingRate=100,
                            SubscriptionPingRate=1000,
                            EnableBuffering=True)
        self.delayWrite(0.2,
                        ItemContainer(ItemName='sample_integer',
                                      Value=17))
        self.delayWrite(0.4,
                        ItemContainer(ItemName='sample_integer',
                                      Value=18))
        self.delayWrite(0.6,
                        ItemContainer(ItemName='sample_integer',
                                      Value=19))
        self.delayWrite(0.8,
                        ItemContainer(ItemName='sample_integer',
                                      Value=20))
        d.addCallback(self._st2_testSPR7_Buffering1)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults(self.TestDeferreds)
    def _st2_testSPR7_Buffering1(self,result):
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0],
            HoldTime=datetime.datetime.now() + \
            datetime.timedelta(0,2))
        d.addCallback(self._cbst2_testSPR7_Buffering1)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbst2_testSPR7_Buffering1(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # The value were never read back, hence they are "changed"
        self.assertEqual(ilist[0].Value,17)
        self.assertEqual(ilist[0].ResultID,None)
        self.assertEqual(ilist[1].Value,18)
        self.assertEqual(ilist[1].ResultID,None)
        self.assertEqual(ilist[2].Value,19)
        self.assertEqual(ilist[2].ResultID,None)
        self.assertEqual(ilist[3].Value,20)
        self.assertEqual(ilist[3].ResultID,None)
        self.assertEqual(Options.get('DataBufferOverflow',None),None)

    ############################################################
    def testSPR8_Buffering2(self):
        ''' Test Buffering with overflow '''
        d = self.initSubscriptionTests()
        self.mkSubscription(d,
                            ItemContainer(ItemName='sample_integer'),
                            ReturnValuesOnReply=True,
                            RequestedSamplingRate=100,
                            SubscriptionPingRate=1000,
                            EnableBuffering=True)
        self.delayWrite(0.2,
                        ItemContainer(ItemName='sample_integer',
                                      Value=17))
        self.delayWrite(0.4,
                        ItemContainer(ItemName='sample_integer',
                                      Value=18))
        self.delayWrite(0.6,
                        ItemContainer(ItemName='sample_integer',
                                      Value=19))
        self.delayWrite(0.8,
                        ItemContainer(ItemName='sample_integer',
                                      Value=20))
        self.delayWrite(1,
                        ItemContainer(ItemName='sample_integer',
                                      Value=21))
        d.addCallback(self._st2_testSPR8_Buffering2)
        # Add default errback
        d.addErrback(log.err)
        return defer.gatherResults(self.TestDeferreds)
    def _st2_testSPR8_Buffering2(self,result):
        d=self.xda.twSubscriptionPolledRefresh\
           (ServerSubHandles=self.TestServerSubHandles[0],
            HoldTime=datetime.datetime.now() + \
            datetime.timedelta(0,3))
        d.addCallback(self._cbst2_testSPR8_Buffering2)
        # Add default errback
        d.addErrback(log.err)
        return d
    def _cbst2_testSPR8_Buffering2(self,(ilist,Options)):
        # There should be no invalid ServerSubHandles
        self.assertEqual([],Options.get('InvalidServerSubHandles',[]))
        # The value were never read back, hence they are "changed"
        self.assertEqual(len(ilist),4)
        self.assertEqual(ilist[0].Value,18)
        self.assertEqual(ilist[0].ResultID,self.OPC_S_DATAQUEUEOVERFLOW)
        self.assertEqual(ilist[1].Value,19)
        self.assertEqual(ilist[1].ResultID,self.OPC_S_DATAQUEUEOVERFLOW)
        self.assertEqual(ilist[2].Value,20)
        self.assertEqual(ilist[2].ResultID,self.OPC_S_DATAQUEUEOVERFLOW)
        self.assertEqual(ilist[3].Value,21)
        self.assertEqual(ilist[3].ResultID,self.OPC_S_DATAQUEUEOVERFLOW)
        self.assertEqual(Options.get('DataBufferOverflow',None),True)


    #del testSubscribe_NoVal
    #del testSubscribe_Val
    #del testSubscribe_Errorneous
    #del testMultiSubscriptions
    #del testSubscriptionCancel
    #del testSPR1_Invalid
    #del testSPR2_NoInitValChange
    #del testSPR3_InitValChange
    #del testSPR4_WaitTime
    #del testSPR5_WaitTime1
    #del testSPR6_WaitTime2
    #del testSPR6_WaitTime3 #
    #del testSPR7_Buffering1
    #del testSPR8_Buffering2
