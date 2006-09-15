#!/usr/bin/env python2.4
""" The ESDSim Server simulates a real IGUANA ESD server
It reads the config files from the file "fieldbus_config.xml"
"""
from twisted.internet.protocol import Factory
from twisted.internet import reactor, defer
from xml.dom import minidom
from PyOPC.protocols.ESD import *

ESDSIM_VERSION = "ESDSIM 0.1 alpha"
ESDSIM_PORT = 1111

class ESDSim(object):
    ''' Dummy class with unimplemented ESD Commands '''

    # Dictionaries for fieldbus elements pointing to xml nodes
    nodelist_seqno = 0
    fanid_dict = {}
    node_dict = {}
    datapoint_dict = {}

    def __init__(self, configfile='fieldbus_config.xml'):
        """ Reads the fieldbus configuration file and
        initializes several dictionaries for all functions """

        self.ESD_VERSION = ESDSIM_VERSION
        self.xmlconf = minidom.parse(configfile)

        # Build a cache of certain data
        # First get all FANTYPES
        fantypes = self.xmlconf.getElementsByTagName('fantype')
        for fantype in fantypes:
            fantype_id = fantype.getAttribute('id')

            # Now get all FANIds
            fanids = fantype.getElementsByTagName('fanid')
            for fanid in fanids:
                fanid_id = fanid.getAttribute('id')
                # Create Dictionary of fanids
                t_fanid = fantype_id+'.'+fanid_id
                self.fanid_dict[t_fanid] = fanid

                # Now get all Nodes
                nodes = fanid.getElementsByTagName('node')
                for node in nodes:
                    node_id = node.getAttribute('id')
                    # Create Dictionary of nodes
                    t_node = t_fanid+'!'+node_id
                    self.node_dict[t_node] = node
                    
                    # Now get all Datapoints
                    datapoints = node.getElementsByTagName('datapoint')
                    for datapoint in datapoints:
                        datapoint_id = datapoint.getAttribute('id')
                        for n in datapoint.childNodes:
                            if n.nodeType == n.ELEMENT_NODE:
                                if n.tagName == 'canonical':
                                    canonical = n.firstChild.data.lower()
                                if n.tagName == 'delay':
                                    delay = n.firstChild.data.lower()

                        # Create Dictionary of datapoints
                        t_datapoint = t_fanid+'!'+datapoint_id+'@'+node_id
                        self.datapoint_dict[t_datapoint] = (datapoint,
                                                            canonical,
                                                            delay)
                                                            
    def Read(self, DpAddress, Encoding):
        ''' Read data from Datapoint '''
        # Check, if dpaddress is available
        if not self.datapoint_dict.has_key(DpAddress):
            raise ESDError(3002,'No such FAN data point')

        # Retrieve cached data
        domaddress, canonical, delay = self.datapoint_dict[DpAddress]

        # Now check encoding
        if Encoding not in dp_encodings(canonical):
            raise ESDError(4007,'Requested encoding not supported by datapoint')

        # Retrieve datapoint value
        value = domaddress.getElementsByTagName('value')[0].firstChild.data

        # Now encode data
        result,enc_value = esd_encode(canonical,Encoding,value)
        
        if result != True:
            raise ESDError(4008,'Error while encoding data')

        # Return after delay
        delay = float(delay)
        if delay != 0:
            d = defer.Deferred()
            d.addCallback(self._Read)
            reactor.callLater(delay,d.callback,(DpAddress,Encoding,enc_value))
            return d
        else:
            return DpAddress,Encoding,enc_value
    def _Read(self,(DpAddress,Encoding,enc_value)):
        return DpAddress,Encoding,enc_value
        
    def Write(self, DpAddress, Encoding, Data):
        """ This function writes data to the fieldbus """
        # Check, if DpAddress is available
        if not self.datapoint_dict.has_key(DpAddress):
            raise ESDError(3002,'No such FAN data point')

        # Retrieve cached data
        domaddress, canonical, delay = self.datapoint_dict[DpAddress]

        # Now check Encoding
        if Encoding not in dp_encodings(canonical):
            raise ESDError(4007,'Unsuitable datapoint encoding')

        # Now encode data
        result,value = esd_decode(canonical,Encoding,Data)

        if result != True:
            raise ESDError(4008,'Error while encoding data')

        # Write datapoint value
        # Create New Text node
        new_value_node = self.xmlconf.createTextNode(value)
        # Get parent dom address
        parent_element = domaddress.getElementsByTagName('value')[0]
        # Get old Text Node
        old_value_node = parent_element.firstChild
        # Replace old with new value
        parent_element.replaceChild(new_value_node,old_value_node)

        # Return after delay
        delay = float(delay)
        if delay != 0:
            d = defer.Deferred()
            d.addCallback(self._Write)
            reactor.callLater(delay,d.callback,None)
            return d
        else:
            return
    def _Write(self,result):
        ''' Just return, nothing else to do here '''
        return
        
    def DPInfo(self, DpAddress):
        """ Return Info about Datapoint """
        # Check, if dpaddress is available
        if not self.datapoint_dict.has_key(DpAddress):
            raise ESDError(3002,'No such FAN data point')

        # Retrieve cached data
        domaddress, canonical, delay = self.datapoint_dict[DpAddress]

        datatype = domaddress.getElementsByTagName('datatype')[0].firstChild.data
        access = domaddress.getElementsByTagName('access')[0].firstChild.data
        dp_name = domaddress.getElementsByTagName('dp_name')[0].firstChild.data
        sid_str = domaddress.getElementsByTagName('sid_str')[0].firstChild.data

        return DpAddress, datatype, dp_encodings(canonical), access, dp_name, sid_str
    
    def NodeInfo(self, NodeAddress):
        """ Return Info about FAN node """
        # Check, if dpaddress is available
        if not self.node_dict.has_key(NodeAddress):
            raise ESDError(3003,'No such FAN node')

        # Retrieved cached data
        domaddress = self.node_dict[NodeAddress]

        nsid_str = domaddress.getElementsByTagName('nsid_str')[0].firstChild.data
        opt1_str = domaddress.getElementsByTagName('opt1_str')[0].firstChild.data
        opt2_str = domaddress.getElementsByTagName('opt2_str')[0].firstChild.data
        dp_num = str(len(domaddress.getElementsByTagName('datapoint')))
                    
        return NodeAddress,dp_num,nsid_str,opt1_str,opt2_str

    def ENodeInfo(self, NodeAddress):
        ''' Return extended NodeInfo = info about node + all datapoints '''
        # Check, if dpaddress is available
        if not self.node_dict.has_key(NodeAddress):
            raise ESDError(3003,'No such FAN node')

        # Now get all according dpaddresses
        domaddress = self.node_dict[NodeAddress]
        datapoints = []
        for dp in domaddress.getElementsByTagName('datapoint'):
            # I do not have the complete dpaddress, so I have
            # to generate it
            dp_id = dp.getAttribute('id')
            i = NodeAddress.find('!')
            DpAddress = NodeAddress[:i+1] + \
                        dp_id + '@' + \
                        NodeAddress[i+1:]
            datapoints.append(self.DPInfo(DpAddress))
        msg = list(self.NodeInfo(NodeAddress))
        msg.append(datapoints)
        return msg

    def NodeList(self):
        ''' List all available nodes on the fieldbus '''
        return 1, self.node_dict.keys()

    def NodeListSeqNo(self):
        ''' Always return 1 '''
        return 1
    def RefreshNodeList(self,fanid):
        ''' No action '''
        pass
    def UpdateNodeList(self,fanid):
        ''' No action '''
        pass

if __name__ == "__main__":
    reactor.listenTCP(ESDSIM_PORT, ESDFactory(ESDSim()))
    reactor.run()

    
    
