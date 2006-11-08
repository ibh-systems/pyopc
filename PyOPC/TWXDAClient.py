#! /usr/bin/env python

'''OPC XMLDA 1.0 Client module based on Twisted'''

import string,random

from twisted.internet import reactor,defer
from twisted.web import client as twclient

import OpcXmlDaSrv_services as OpcSrv
from OPCContainers import *

def gen_twoperation(op):
    ''' Generate a Twisted based OPC operation '''
    
    def twoperation(self, *IClist, **Options):
        ''' OPC Operation '''

        x = getattr(OpcSrv,op+'SoapIn')()

        # Apply General attributes (Options)
        self.fill_tc(x,IClist,Options)

        # All Options should be gone, if not raise error
        if Options:
            raise TypeError('Unknown options given: %s',str(Options))

        # Serialize typecode
        SOAPMessage = str(ZSI.SoapWriter().serialize(x,unique=True))

        headers = {
            'SOAPAction':'http://opcfoundation.org/webservices/XMLDA/1.0/'+op,
            'content-type':'text/xml; charset=utf-8',
            'content-length':str(len(SOAPMessage))}

        # If '/' is not the end of the server address, the operation
        # fails. This should better be handled by the server
        if self.OPCServerAddress[-1] != '/':
            self.OPCServerAddress += '/'

        scheme, host, port, path = twclient._parse(self.OPCServerAddress)


        factory = twclient.HTTPClientFactory(self.OPCServerAddress,
                                             method='POST',
                                             postdata=SOAPMessage,
                                             headers=headers,
                                             agent='Twisted OPC XMLDA Client',
                                             timeout=0)
        if scheme == 'https':
            from twisted.internet import ssl
            if contextFactory is None:
                contextFactory = ssl.ClientContextFactory()
            reactor.connectSSL(host,port,factory,contextFactory)
        else:
            reactor.connectTCP(host,port,factory)
            
        # Add handle___Reponse to the callback chain
        n = getattr(self,'twhandle'+op)
        factory.deferred.addCallback(n)
        factory.deferred.addErrback(handleFault)
        return factory.deferred
    return twoperation

def handleFault(failure):
    ''' Handle SOAP Faults '''
    # SOAP Faults will have be an Error 500, hence value.args[2] have to
    # be used, args[0] = errno, args[1]=error message, args[2] = response data
    data = failure.value.args[2]
    ps = ZSI.ParsedSoap(data)
    if ps.IsAFault():
        # Raise an error if it is a fault
        f = ZSI.FaultFromFaultMessage(ps)
        raise f

def gen_twhandleResult(op):
    ''' Generate Result handler '''

    def handleResult(self, data):
        ps = ZSI.ParsedSoap(data)
        e = ps.body_root
        if ps.IsAFault():
            # Should never happen as it should be handled by errback
            # Raise an error if it is a fault
            f = ZSI.FaultFromFaultMessage(ps)
            raise f

        tc_out = getattr(OpcSrv,op+'SoapOut')
        tc_out = ps.Parse(tc_out.typecode)
        outIClist,outOptions = self.read_tc(tc_out)
        
        return outIClist,outOptions
    return handleResult


class TWXDAClient(OPCOperation):
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
        
        # Build a fancy and unique request handle
        random.seed()
        c = string.letters + string.digits
        s = ''.join([c[random.randint(0,len(c)-1)] for b in range(10)])
        self.ClientRequestHandle = 'ZSI_'+s
        
    # Generate twisted based OPC operations
    # These are pairs, the second is the callback operation
    twGetStatus = gen_twoperation('GetStatus')
    twhandleGetStatus=gen_twhandleResult('GetStatus')

    twRead = gen_twoperation('Read')
    twhandleRead=gen_twhandleResult('Read')

    twWrite = gen_twoperation('Write')
    twhandleWrite=gen_twhandleResult('Write')

    twSubscribe = gen_twoperation('Subscribe')
    twhandleSubscribe=gen_twhandleResult('Subscribe')

    twSubscriptionPolledRefresh= gen_twoperation('SubscriptionPolledRefresh')
    twhandleSubscriptionPolledRefresh=gen_twhandleResult('SubscriptionPolledRefresh')

    twSubscriptionCancel = gen_twoperation('SubscriptionCancel')
    twhandleSubscriptionCancel=gen_twhandleResult('SubscriptionCancel')

    twBrowse = gen_twoperation('Browse')
    twhandleBrowse=gen_twhandleResult('Browse')

    twGetProperties = gen_twoperation('GetProperties')
    twhandleGetProperties=gen_twhandleResult('GetProperties')


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
        

    # Possible Sample Clients

    # Default sample server (PyOPC default)
    address = 'http://violin.qwer.tk:8000/'
    
    xda = TWXDAClient(OPCServerAddress=address)

    def handleResult((ic,op)):
        print op
        print ic
        reactor.stop()

    def handleError(failure):
        print "An Error occured"
        print failure.getTraceback()
        reactor.stop()
        

    d = xda.twGetStatus()
    d.addCallback(handleResult)
    d.addErrback(handleError)

    reactor.run()
    
