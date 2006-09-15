#!/usr/bin/env python2.4
""" Protocol, Factory and a simple Client for the Extended Service Daemon (ESD) protocol
"""

from twisted.protocols import basic, policies
from twisted.internet import protocol, reactor, defer
from twisted.python.failure import Failure
import time, base64, re

class ESDError(Exception):
    pass
    
class ESDServerError(Exception):
    pass

class ESDClientError(Exception):
    pass


def tobinhex(data):
    """ Convert any kind of data to a hexadecimal format with
    the base64.b16encode function """

    s_data = unicode(data).encode('utf-8')
    hex_data = base64.b16encode(s_data)
    l_binhex=[]

    for i in range(len(hex_data))[::2]:
        l_binhex.append(hex_data[i:i+2])

    return '"%s"' % ' '.join(l_binhex).upper()

def dp_encodings(canonical):
    """ Return a tuple of possible encodings for a certain
    canonical data type of a datapoint """

    # To circumvent case troubles
    canonical=canonical.lower()

    if canonical == 'float':
        return('BINHEX','STRING','SCALARBIN')
    elif canonical == 'time':
        return('BINHEX','STRING','TIME')
    elif canonical == 'string':
        return('BINHEX','STRING')
    else:
        return('BINHEX')

def esd_encode(canonical,encoding,data):
    """ Encode canonical fieldbus data into one of ESD encodings """
    if canonical == 'float':
        # Do a sanity check
        try:
            dummy = float(data)
        except ValueError:
            return False,data
        
        if encoding == 'SCALARBIN':
            return True,data
        elif encoding == 'STRING':
            return True, '"%s"' % data.strip('"')
        elif encoding == 'BINHEX':
            return True,tobinhex(data)
        else:
            return False,data
        
    elif canonical == 'time':
        # Do a sanity check
        try:
            dummy = time.localtime(float(data))
        except ValueError:
            return False,data

        if encoding == 'TIME':
            return True,data
        elif encoding == 'STRING':
            return True, '"%s"' % time.asctime(time.localtime(float(data)))
        elif encoding == 'BINHEX':
            return True,tobinhex(data)
        else:
            return False,data

    elif canonical == 'string':
        if encoding == 'STRING':
            return True,'"%s"' % data.strip('"')
        elif encoding == 'BINHEX':
            return True,tobinhex(data)
        else:
            return False,data

    else:
        # return in BINHEX format
        return True,tobinhex(data)

def esd_decode(canonical,encoding,enc_value):
    """ Convert data in specified encoding to canonical fieldbus
    encoding and return it """

    # Make sure it's a string
    buf = str(enc_value)
    # Strip all Whitespace
    buf = buf.strip()
    # Strip beginning and trailing "
    buf = buf.strip('"')

    if encoding == 'BINHEX':
        # Decode binhex
        # remove spaces between digits
        buf = re.sub(' ','',buf)
        try:
            buf = base64.b16decode(buf)
        except TypeError:
            return False,buf

    if canonical == 'float':
        # Sanity Check:
        try:
            dummy = float(buf)
        except ValueError:
            return False,buf

    if canonical == 'time':
        # Sanity Check:
        try:
            dummy = time.localtime(float(data))
        except ValueError:
            return False,buf
                    
    return True,buf

def split_dquote(line):
  delimiter_OutString = set(' "')
  delimiter_InString = set('"')
  # Set delimiter to outside string
  delimiter = delimiter_OutString
  reslist = []
  s = []
  for c in line:
    if c in delimiter:
      if s or (c == '"' and delimiter == delimiter_InString):
        # Append any collected character sequence
        reslist.append(''.join(s))
        s = []
      if c == '"':
        if delimiter == delimiter_InString:
          delimiter = delimiter_OutString
        else:
          delimiter = delimiter_InString
    else:
      s.append(c)
          
  # Append the rest
  if s:
    reslist.append(''.join(s))
  return reslist

def DecodeESDAddress(address):
    ''' Decode ESD address format and return its parts '''
    # First cut address on first '!'
    tup = address.split('!',1)
    if len(tup) != 2:
        raise ValueError('Invalid ESD address')
    part1,part2 = tup
    # Now try to split the first part, the FANid
    tup = part1.split('.',1)
    if len(tup)==2:
        fantype,fanid = tup
    else:
        fantype = None
        fanid = tup[0]
    # Now split the second part
    tup = part2.split('@',1)
    if len(tup)==2:
        dpaddress, nodeaddress = tup
    else:
        dpaddress = None
        nodeaddress = tup[0]
    return fantype,fanid,nodeaddress,dpaddress


class ESD(basic.LineOnlyReceiver, policies.TimeoutMixin):

    timeout = 600
    DEBUG=True

    def __init__(self, esdsrv=None):
        self.esdsrv = esdsrv

    def timeoutConnection(self):
        msg = '%s Timeout. Try talking faster next time!' % (self.host,)
        self.sendLine(msg.encode('ascii'))
        self.transport.loseConnection()

    # No greeting: This confuses the client!
    # def connectionMade(self):
    #    self.sendLine(self.do_VERSION(None))

    def lineReceived(self, line):
        print 'READ: ', line
        self.resetTimeout()
        lbuf = line.split(None, 1)
        if lbuf:
            command = lbuf[0]
            if len(lbuf) == 1:
                params = ''
            else:
                params = lbuf[1]
            # Handle QUIT command seperately
            if command.upper() == 'QUIT':
                self.sendLine('0 Bye')
                self.transport.loseConnection()
            else:
                method = getattr(self, 'do_' + command.upper(), None)
                if method:
                    d = defer.maybeDeferred(method, params)
                    d.addErrback(self.handle_Error)
                    d.addCallback(self.sendLines)
                else:
                    self.sendLine('200 Unknown Command')
        else:
            self.sendLine('100 Invalid Syntax')

    def handle_Error(self,failure):
        if failure.check(NotImplementedError):
            msg = '1000 This command is not implemented'
        elif failure.check(ESDError) and len(failure.value.args) == 2:
            msg = '%s %s' % (failure.value.args[0],failure.value.args[1])
        else:
            if self.DEBUG:
                msg = '9999 Server Error: \n%s: %s\n%s' % (failure.type,
                                                          failure.getErrorMessage(),
                                                          failure.getTraceback())
            else:
                msg = '9999 Unknown Server Error'
        return msg

    def returnOK(self,result=None):
        msg = '0 OK'
        return msg

    def sendLines(self,emsg):
        ''' Either send one (basic) line or a list of lines in extended style '''
        if isinstance(emsg,basestring):
            print 'WRITE:', emsg
            self.sendLine(emsg.encode('ascii'))
        elif isinstance(emsg,(tuple,list)):
            for line in emsg:
                print 'WRITE:', line
                self.sendLine(line.encode('ascii'))
            # End extended response with single '.'
            self.sendLine('.')

    def do_READ(self,rest):
        l=rest.split()
        if len(l) != 2:
            raise ESDError(201,'Invalid READ syntax. The format should be: "READ DPAddress Encoding"')

        DpAddress, Encoding = l
        d = defer.maybeDeferred(self.factory.cmds.Read, DpAddress, Encoding)
        d.addCallback(self._do_READ)
        return d
    def _do_READ(self,(DpAddress,Encoding,Data)):
        msg = '0 %s %s %s' % (DpAddress, Encoding, Data)
        return msg

    def do_WRITE(self,rest):
        l=rest.split(None,2)
        # Only split in 3, the last one may be BINHEX like "29 39 18"
        if len(l) != 3:
            raise ESDError(301,'Invalid WRITE syntax. The format should be: "WRITE DpAddress Encoding Data"')

        DpAddress, Encoding, Data = l
        d = defer.maybeDeferred(self.factory.cmds.Write, DpAddress, Encoding, Data)
        d.addCallback(self.returnOK)
        return d

    def do_DPINFO(self,rest):
        l = rest.split()
        if len(l) != 1:
            raise ESDError(401,'Invalid syntax: Must be of format "DPINFO DpAddress"')
        DpAddress = l[0]
        d = defer.maybeDeferred(self.factory.cmds.DPInfo, DpAddress)
        d.addCallback(self._do_DPINFO)
        return d
    def _do_DPINFO(self,(DpAddress,DataType,SetOfEncodings,Access,dp_name,sid_str)):
        # SetOfEncodings may be a list/tuple, convert it to e.g. "SCALARBIN:BINHEX"
        if isinstance(SetOfEncodings,(tuple,list)):
            SetOfEncodings = ':'.join(SetOfEncodings)
            
        msg = '0 %s %s %s %s "%s" "%s"' % (
            DpAddress,
            DataType,
            SetOfEncodings,
            Access,
            dp_name.strip('"'),
            sid_str.strip('"'))
        return msg

    def do_NODEINFO(self,rest):
        l = rest.split()
        if len(l) != 1:
            raise ESDError(501,'Invalid syntax: Must be of format "NODEINFO NodeAddress"')
        NodeAddress = l[0]
        d = defer.maybeDeferred(self.factory.cmds.NodeInfo, NodeAddress)
        d.addCallback(self._do_NODEINFO)
        return d
    def _do_NODEINFO(self,(NodeAddress,dp_num,nsid_str,opt1_str,opt2_str)):
        msg = '0 %s %s "%s" "%s" "%s"' % (
            NodeAddress,
            dp_num,
            nsid_str.strip('"'),
            opt1_str.strip('"'),
            opt2_str.strip('"'))
        return msg

    def do_ENODEINFO(self,rest):
        l = rest.split()
        if len(l) != 1:
            raise ESDError(601,'Invalid syntax: Must be of format "ENODEINFO NodeAddress"')
        NodeAddress = l[0]
        d = defer.maybeDeferred(self.factory.cmds.ENodeInfo, NodeAddress)
        d.addCallback(self._do_ENODEINFO)
        return d
    def _do_ENODEINFO(self,(NodeAddress,dp_num,nsid_str,opt1_str,opt2_str,datapoints)):
        emsg = []
        msg = '0 %s %s "%s" "%s" "%s"' % (
            NodeAddress,
            dp_num,
            nsid_str.strip('"'),
            opt1_str.strip('"'),
            opt2_str.strip('"'))
        emsg.append(msg)
        for dp in datapoints:
            DpAddress,DataType,SetOfEncodings,Access,dp_name,sid_str = dp
            if isinstance(SetOfEncodings,(tuple,list)):
                SetOfEncodings = ':'.join(SetOfEncodings)
            msg = '%s %s %s %s "%s" "%s"' % (
                DpAddress,
                DataType,
                SetOfEncodings,
                Access,
                dp_name.strip('"'),
                sid_str.strip('"'))
            emsg.append(msg)
        return emsg
            
    def do_NODELIST(self,rest):
        if len(rest.split()):
            raise ESDError(701,'Invalid syntax: Must be of format "NODELIST"')
        d = defer.maybeDeferred(self.factory.cmds.NodeList)
        d.addCallback(self._do_NODELIST)
        return d
    def _do_NODELIST(self,(NodeListSeqNo,NodeAddresses)):
        emsg = []
        emsg.append('0 %s' % NodeListSeqNo)
        for NodeAddress in NodeAddresses:
            emsg.append(NodeAddress)
        return emsg

    def do_NODELISTSEQNO(self,rest):
        if len(rest.split()):
            raise ESDError(801,'Invalid syntax: Must be of format "NODELISTSEQNO"')
        d = defer.maybeDeferred(self.factory.cmds.NodeListSeqNo)
        d.addCallback(self._do_NODELISTSEQNO)
        return d
    def _do_NODELISTSEQNO(self,seqno):
        msg = '0 %s' % seqno
        return msg

    def do_REFRESHNODELIST(self,rest):
        l = rest.split()
        if len(l) == 1:
            fanid = l[0]
        elif len(l) == 0:
            fanid = ''
        else:
            raise ESDError(901,'Invalid syntax: Must be of format "REFRESHNODELIST [FANID]"')
        d = defer.maybeDeferred(self.factory.cmds.RefreshNodeList,fanid)
        d.addCallback(self.returnOK)
        return d

    def do_UPDATENODELIST(self,rest):
        l = rest.split()
        if len(l) == 1:
            fanid = l[0]
        elif len(l) == 0:
            fanid = ''
        else:
            raise ESDError(951,'Invalid syntax: Must be of format "UPDATENODELIST [FANID]"')
        d = defer.maybeDeferred(self.factory.cmds.UpdateNodeList,fanid)
        d.addCallback(self.returnOK)
        return d

    def do_VERSION(self, rest):
        version = getattr(self.factory.cmds,'ESD_VERSION',None)
        if version == None:
            version = 'Unknown Version'
        msg = '0 ESD Version %s' % version
        return msg
        

class ESDFactory(protocol.ServerFactory):

    protocol = ESD

    def __init__(self, cmds):
        self.cmds = cmds
    
class ESDClient(basic.LineOnlyReceiver, policies.TimeoutMixin):
    ''' ESD Client '''

    ExtendedResponseCmnds = set(('ENODEINFO','NODELIST'))
    

    def connectionMade(self):
        ''' Assemble the request and send it '''
        # Initialize variables for multiline reception
        self.ExtendedResponse = False
        self.ExtendedMsg = []
        msg = '%s %s' % (self.factory.command.upper(), ' '.join(self.factory.args))
        self.sendLine(msg.encode('ascii'))
        self.setTimeout(self.factory.timeout)
        
    def timeoutConnection(self):
        if not self.factory.deferred.called:
            self.transport.loseConnection()
            self.factory.deferred.errback(Failure(ESDClientError(8000, 'A Timeout occurred')))
                
    def lineReceived(self,line):
        if self.ExtendedResponse == True:
            if line != '.':
                self.ExtendedMsg.append(line)
            else:
                # Extended message has ended
                self.Multiline = False
                # Call method
                self.DoResponse(self.ExtendedMsg)
        else:
            result, data = line.split(None,1)
            if result != '0':
                self.transport.loseConnection()
                self.factory.deferred.errback(Failure(ESDClientError(result, data)))
            else:
                if self.factory.command.upper() in self.ExtendedResponseCmnds:
                    self.ExtendedResponse = True
                    self.ExtendedMsg.append(data)
                else:
                    self.DoResponse(data)
                
    def DoResponse(self,data):
        self.transport.loseConnection()
        func = getattr(self,self.factory.command+'Response',None)
        try: 
            result = func(data)
        except (ESDServerError, ESDClientError), err_o:
            self.factory.deferred.errback(Failure(err_o))
        else:
            self.factory.deferred.callback(func(data))
    
    def ReadResponse(self, data):
        restup = data.split(None,2)
        if len(restup) != 3:
            raise ESDServerError((9999,'Invalid format of result message'))
        return restup
    def WriteResponse(self, data):
        'Nothing to do here'
        pass
    def DPInfoResponse(self, data):
        restup = data.split(None,4)
        if len(restup) != 5:
            raise ESDServerError((9999,'Invalid format of result message'))
        DpAddress, DataType, SetOfEncodings, Access, data = restup
        SetOfEncodings = SetOfEncodings.split(':')
        restup = split_dquote(data)
        if len(restup) != 2:
            raise ESDServerError((9999,'Invalid format of result message'))
        return [DpAddress, DataType, SetOfEncodings, Access]+restup
    def NodeInfoResponse(self, data):
        restup = data.split(None,2)
        if len(restup) != 3:
            raise ESDServerError((9999,'Invalid format of result message'))
        NodeAddress, dp_num, data = restup
        restup = split_dquote(data)
        if len(restup) != 3:
            raise ESDServerError((9999,'Invalid format of result message'))
        return [NodeAddress, dp_num]+restup
    def ENodeInfoResponse(self, data):
        msg = []
        msg.append(self.NodeInfoResponse(data[0]))
        for dp in data[1:]:
            msg.append(self.DPInfoResponse(dp))
        return msg
    def NodeListResponse(self, nodes):
        return nodes
    def NodeListSeqNoResponse(self, data):
        return data
    def RefreshNodeListResponse(self, data):
        return None
    def UpdateNodeListResponse(self, data):
        return None
     

class ESDClientFactory(protocol.ClientFactory):
    
    protocol = ESDClient
    
    def __init__(self, command, *kl):
        self.deferred = defer.Deferred()
        self.command = command
        self.args = kl
    
class SimpleClient(object):

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
    
    def Read(self, DpAddress, Encoding):
        factory = ESDClientFactory('Read',DpAddress, Encoding)
        factory.timeout = self.timeout
        reactor.connectTCP(self.host,self.port,factory)
        return factory.deferred
    def Write(self, DpAddress, Encoding, Data):
        factory = ESDClientFactory('Write',DpAddress, Encoding, Data)
        factory.timeout = self.timeout
        reactor.connectTCP(self.host,self.port,factory)
        return factory.deferred
    def DPInfo(self, DpAddress):
        factory = ESDClientFactory('DPInfo',DpAddress)
        factory.timeout = self.timeout
        reactor.connectTCP(self.host,self.port,factory)
        return factory.deferred
    def NodeInfo(self, NodeAddress):
        factory = ESDClientFactory('NodeInfo',NodeAddress)
        factory.timeout = self.timeout
        reactor.connectTCP(self.host,self.port,factory)
        return factory.deferred
    def ENodeInfo(self, NodeAddress):
        factory = ESDClientFactory('ENodeInfo',NodeAddress)
        factory.timeout = self.timeout
        reactor.connectTCP(self.host,self.port,factory)
        return factory.deferred
    def NodeList(self):
        factory = ESDClientFactory('NodeList')
        factory.timeout = self.timeout
        reactor.connectTCP(self.host,self.port,factory)
        return factory.deferred
    def NodeListSeqNo(self):
        factory = ESDClientFactory('NodeListSeqNo')
        factory.timeout = self.timeout
        reactor.connectTCP(self.host,self.port,factory)
        return factory.deferred
    def RefreshNodeList(self,fanid):
        factory = ESDClientFactory('RefreshNodeList',fanid)
        factory.timeout = self.timeout
        reactor.connectTCP(self.host,self.port,factory)
        return factory.deferred
    def UpdateNodeList(self,fanid):
        factory = ESDClientFactory('UpdateNodeList',fanid)
        factory.timeout = self.timeout
        reactor.connectTCP(self.host,self.port,factory)
        return factory.deferred

if __name__ == "__main__":

    class ESDCommands(object):
        ''' Dummy class with unimplemented ESD Commands '''

        ESD_VERSION = "0.1 alpha"
        def Read(self, DpAddress, Encoding):
            return '1:2:3','STRING',"Hello World"
        def Write(self, DpAddress, Encoding, Data):
            return
        def DPInfo(self, DpAddress):
            return '1:2:3',114,['SCALARBIN','BINHEX'],'RW','Text Point',''
        def NodeInfo(self, NodeAddress):
            return '4:5:6',3,'TestNode','TestLocation',''
        def ENodeInfo(self, NodeAddress):
            return '4:5:6',3,'TestNode','TestLocation','',[
                ('1:2:3',23,['SCALARBIN','BINHEX'],'RW','TextPoint',''),
                ('1:2:4',36,['SCALARBIN','BINHEX'],'RO','TextPoint2','')]
        def NodeList(self):
            return 139,['1:2:3','2:2:4','5:6:3']
        def NodeListSeqNo(self):
            return 1
        def RefreshNodeList(self,fanid):
            raise NotImplementedError
        def UpdateNodeList(self,fanid):
            raise NotImplementedError
    
    reactor.listenTCP(1111, ESDFactory(ESDCommands()))
    
    def PrintArgs(result,cmd,stop=False):
        print cmd,':',result
        if stop: 
            reactor.callLater(2,reactor.stop)
    def PrintErr(failure,cmd,stop=False):
        print cmd,':',failure.value
        if stop: 
            reactor.callLater(2,reactor.stop)
    
    # Test the server
    s = SimpleClient('localhost',1111,timeout=15)
    s.Read('asdf', 'BINHEX').addCallback(PrintArgs,'Read').addErrback(PrintErr,'Read')
    s.Write('asdf','BINHEX','asdf').addCallback(PrintArgs,'Write').addErrback(PrintErr,'Write')
    s.DPInfo('asdf').addCallback(PrintArgs,'DPInfo').addErrback(PrintErr,'DPInfo')
    s.NodeInfo('asdf').addCallback(PrintArgs,'NodeInfo').addErrback(PrintErr,'NodeInfo')
    s.ENodeInfo('asdf').addCallback(PrintArgs,'ENodeInfo').addErrback(PrintErr,'ENodeInfo')
    s.NodeList().addCallback(PrintArgs,'NodeList').addErrback(PrintErr,'NodeList')
    s.NodeListSeqNo().addCallback(PrintArgs,'NodeListSeqNo').addErrback(PrintErr,'NodeListSeqNo')
    s.RefreshNodeList('asd').addCallback(PrintArgs,'RefreshNodeList').addErrback(PrintErr,'RefreshNodeList')
    s.UpdateNodeList('asdf').addCallback(PrintArgs,'UpdateNodeList',True).addErrback(PrintErr,'UpdateNodeList',True)

    reactor.run()
