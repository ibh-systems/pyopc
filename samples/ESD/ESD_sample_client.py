#!/usr/bin/python

''' Example ESD Client that queries a ESD server on localhost:1111'''

from PyOPC.protocols.ESD import SimpleClient
from twisted.internet import reactor

def PrintArgs(result,cmd,stop=False):
    print cmd,':',result
    if stop: 
        reactor.callLater(2,reactor.stop)
def PrintErr(failure,cmd,stop=False):
    print cmd,':',failure.value
    if stop: 
        reactor.callLater(2,reactor.stop)

if __name__ == '__main__':        
    # Connect to local ESD Server
    s = SimpleClient('localhost',1111)
    s.Read('LON.GATE2!11@01:02:03:04:08:06','BINHEX').addCallback(PrintArgs,'Read').addErrback(PrintErr,'Read')
    s.Write('LON.GATE1!11@01:02:03:04:05:07','STRING','12').addCallback(PrintArgs,'Write').addErrback(PrintErr,'Write')
    s.DPInfo('LON.GATE2!11@01:02:03:04:08:06').addCallback(PrintArgs,'DPInfo').addErrback(PrintErr,'DPInfo')
    s.NodeList().addCallback(PrintArgs,'NodeList').addErrback(PrintErr,'NodeList')
    s.NodeInfo('LON.GATE2!01:02:03:04:08:06').addCallback(PrintArgs,'NodeInfo').addErrback(PrintErr,'NodeInfo')
    s.NodeInfo('CUSTOM.NASA1!01:02:05:04:05:06').addCallback(PrintArgs,'NodeInfo').addErrback(PrintErr,'NodeInfo')
    s.NodeInfo('LON.GATE1!01:02:03:04:05:06').addCallback(PrintArgs,'NodeInfo').addErrback(PrintErr,'NodeInfo')
    s.NodeInfo('LON.GATE1!01:02:03:04:05:07').addCallback(PrintArgs,'NodeInfo').addErrback(PrintErr,'NodeInfo')
    s.ENodeInfo('LON.GATE2!01:02:03:04:08:06').addCallback(PrintArgs,'ENodeInfo').addErrback(PrintErr,'ENodeInfo')
    s.ENodeInfo('CUSTOM.NASA1!01:02:05:04:05:06').addCallback(PrintArgs,'ENodeInfo').addErrback(PrintErr,'ENodeInfo')
    s.ENodeInfo('LON.GATE1!01:02:03:04:05:06').addCallback(PrintArgs,'ENodeInfo').addErrback(PrintErr,'ENodeInfo')
    s.ENodeInfo('LON.GATE1!01:02:03:04:05:07').addCallback(PrintArgs,'ENodeInfo').addErrback(PrintErr,'ENodeInfo')
    s.NodeListSeqNo().addCallback(PrintArgs,'NodeListSeqNo').addErrback(PrintErr,'NodeListSeqNo')
    s.RefreshNodeList('asd').addCallback(PrintArgs,'RefreshNodeList').addErrback(PrintErr,'RefreshNodeList')
    s.UpdateNodeList('asdf').addCallback(PrintArgs,'UpdateNodeList',True).addErrback(PrintErr,'UpdateNodeList',True)
    
    reactor.run()
