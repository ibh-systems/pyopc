''' XMLDA to ESD proxy '''
import twisted
from twisted.internet import reactor,defer
from twisted.python import log

from PyOPC.protocols import ESD
from PyOPC.XDAServer import XDAServer
from PyOPC.XDAServer import ItemPairHolder
from PyOPC.OPCContainers import *



class ESDProxy(XDAServer):
    ''' Class that implements a proxy between OPC-XMLDA and an ESD server'''

    NS_ESD = 'http://qwer.tk/ESD'
    
    ESD_E_READ = QName(NS_ESD,'E_READ')
    ESD_E_WRITE = QName(NS_ESD,'E_WRITE')
    ESD_E_DPINFO = QName(NS_ESD,'E_DPINFO')
    ESD_E_NODEINFO = QName(NS_ESD,'E_NODEINFO')
    ESD_E_INVALIDENCODING = QName(NS_ESD,'E_INVALIDENCODING')

    OPCServerAddress = '/'
    SupportedLocaleIDs = ('en-us',)

    BrowseDelimiter = '/'

    # Status specifics
    StatusInfo = 'ESD <-> XMLDA Proxy'

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

    MkItemProperties = False

    def __init__(self,*kl,**kd):
        ''' Initialize Test Server '''
        # Initilize Data for the ESD Client
        self.esd_host = kd.get('esd_host','localhost')
        self.esd_port = kd.get('esd_port',1111)

        bd = kd.get('BrowseDelimiter',None)
        if bd:
            self.BrowseDelimiter = bd

        # Predefined Item Values
        self.OPCItemDict = self.mkItems(self.OPCItems)
        super(ESDProxy,self).__init__(self,*kl,**kd)

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
        ''' Read data from a ESD server '''
        # Here all results will be stored
        self.read_results = []
        dlist = []
        for seq,(inItem,outItem) in enumerate(IPH):
            # Store sequence for enabling assemblage later
            inItem.Sequence = seq
            d = self.ReadESD(inItem,outItem)
            dlist.append(d)
        return defer.DeferredList(dlist).addCallback(self._cbRead,(IPH,inOptions,outOptions))
    
    def ReadESD(self,inItem,outItem):
        ''' Read Properties from ESD '''
        lpath = inItem.ItemName.strip('/').split(self.BrowseDelimiter)
        if len(lpath) != 5:
            # Invalid address
            outItem.ResultID = self.OPC_E_INVALIDITEMNAME
            self.read_results.append((inItem.Sequence,inItem,outItem))
            return defer.succeed(None)
        else:
            fantype,fanid,nodeaddress,dpaddress,encoding = lpath
            # Retrieve Node properties
            esd = ESD.SimpleClient(self.esd_host,self.esd_port)
            d = esd.Read('%s.%s!%s@%s' % (fantype, fanid, dpaddress, nodeaddress),encoding)
            d.addCallback(self._cbReadESD,inItem,outItem) 
            d.addErrback(self._errRead,inItem,outItem)
            return d
        
    def _cbReadESD(self,(NodeAddress,encoding,data),
                                 inItem,outItem):
        ''' Handle result of ESD Read '''
        outItem.Value=data
        outItem.QualityField='good'
        outItem.Timestamp = datetime.datetime.now()
        self.read_results.append((inItem.Sequence,inItem,outItem))
    
    def _cbRead(self,result,(IPH,inOptions,outOptions)):
        ''' Assemble IPH and return it '''
        # Sort results so that sequence is correct again
        self.read_results.sort()
        rIPH = ItemPairHolder()
        for i,inItem,outItem in self.read_results:
            rIPH.append(inItem,outItem)
        return super(ESDProxy,self).Read((rIPH,
                                          inOptions,
                                          outOptions))
    
    def _errRead(self, failure, inItem, outItem):
        ''' Fill errorneous property '''
        outItem.ResultID = self.ESD_E_READ
        outItem.ErrorText = str(failure.value.args)
        self.read_results.append((inItem.Sequence,inItem,outItem))
        newIPH = ItemPairHolder()
        
    def Write(self,(IPH,inOptions,outOptions)):
        ''' Write to the item dictionary '''
        # Here all results will be stored
        self.write_results = []
        dlist = []
        for seq,(inItem,outItem) in enumerate(IPH):
            # Store sequence for enabling assemblage later
            inItem.Sequence = seq
            d = self.WriteESD(inItem,outItem)
            dlist.append(d)
        return defer.DeferredList(dlist).addCallback(self._cbWrite,(IPH,inOptions,outOptions))
    
    def WriteESD(self,inItem,outItem):
        ''' Write Properties to ESD server '''
        lpath = inItem.ItemName.strip('/').split(self.BrowseDelimiter)
        if len(lpath) != 5:
            # Invalid address
            outItem.ResultID = self.OPC_E_INVALIDITEMNAME
            self.write_results.append((inItem.Sequence,inItem,outItem))
            return defer.succeed(None)
        else:
            fantype,fanid,nodeaddress,dpaddress,encoding = lpath
            # Retrieve Node properties
            if isinstance(inItem.Value,basestring):
                value = '"%s"' % inItem.Value
            elif isinstance(inItem.Value,(float,long,int)):
                value = str(inItem.Value)
            esd = ESD.SimpleClient(self.esd_host,self.esd_port)
            d = esd.Write('%s.%s!%s@%s' % (fantype, fanid, dpaddress, nodeaddress),encoding,value)
            d.addCallback(self._cbWriteESD,inItem,outItem) 
            d.addErrback(self._errWrite,inItem,outItem)
            return d
        
    def _cbWriteESD(self,result,inItem,outItem):
        ''' Handle result of ESD Write '''
        # Nothing to do
        pass
    
    def _cbWrite(self,result,(IPH,inOptions,outOptions)):
        ''' Assemble IPH and return it '''
        # Sort results so that sequence is correct again
        self.write_results.sort()
        rIPH = ItemPairHolder()
        for i,inItem,outItem in self.write_results:
            rIPH.append(inItem,outItem)
        return super(ESDProxy,self).Write((rIPH,
                                           inOptions,
                                           outOptions))
    
    def _errWrite(self, failure, inItem, outItem):
        ''' Fill errorneous property '''
        outItem.ResultID = self.ESD_E_WRITE
        outItem.ErrorText = str(failure.value.args)
        self.write_results.append((inItem.Sequence,inItem,outItem))
        newIPH = ItemPairHolder()

        #for inItem,outItem in IPH:
            #key = mkItemKey(inItem)
            #if key and outItem.IsEmpty:
                #WriteItem = self.OPCItemDict.get(key,None)
                #if not WriteItem:
                    ## No such item, create new one
                    #WriteItem = ItemContainer()
                    #self.OPCItemDict[key] = WriteItem
                ## Only write what is not None
                #if inItem.Value:
                    #WriteItem.Value = inItem.Value
                #if inItem.Timestamp:
                    #WriteItem.Timestamp = inItem.Timestamp
                #else:
                    #WriteItem.Timestamp = datetime.datetime.now()
                #if inItem.QualityField:
                    #WriteItem.QualityField = inItem.QualityField
                #if inItem.LimitField:
                    #WriteItem.LimitField = inItem.LimitField
                #if inItem.VendorField:
                    #WriteItem.VendorField = inItem.VendorField
                
        ## Call the superclass' write in a deferred style
        ## Else possible Reads would be blocking
        #d = defer.maybeDeferred(super(ESDProxy,self).Write,
                                #(IPH,inOptions,outOptions))
        ## Add errback, because if not, no tracebacks are displayed
        #d.addErrback(log.err)
        #return d

    def Browse(self,(IPH,inOptions,outOptions)):
        ''' Retrieve nodes/datapoints/encodings from the ESD server
        '''
        # ItemPath dekodieren
        
        path = inOptions.get('ItemName','')
        # Remove starting/trailing delimiter
        path = path.strip(self.BrowseDelimiter)
        if path:
            # Split it to 4 list items maximum
            lpath = path.split(self.BrowseDelimiter)
        else:
            lpath = []
        # The length of lpath directs the browsing
        esd = ESD.SimpleClient(self.esd_host,self.esd_port)
        if len(lpath) < 3:
            d = esd.NodeList()
        elif len(lpath) == 3:
            d = esd.ENodeInfo('%s.%s!%s' % (lpath[0],lpath[1],lpath[2]))
        elif len(lpath) == 4:
            d = esd.DPInfo('%s.%s!%s@%s' % (lpath[0],lpath[1],lpath[3],lpath[2]))
        else:
            raise ESD.ESDClientError('3008','Invalid browse path')
            
        d.addCallback(self._cbBrowse,(IPH,inOptions,outOptions), lpath)
        return d

    def _cbBrowse(self,nodes,(IPH,inOptions,outOptions),lpath):
        bd = self.BrowseDelimiter
        if len(lpath) < 3:
            # The result is a nodelist
            dec_nodes = []
            spath = set()
            for node in nodes[1:]:
                dec_nodes.append(ESD.DecodeESDAddress(node))
            # According to the browse request, only some information will be displayed
            if len(lpath) == 0:
                # Only append the FANTYPE
                # Returns /FANTYPE
                for dec_node in dec_nodes:
                    spath.add('%s%s' % (bd,dec_node[0]))
                for buf in spath:
                    IPH.append(ItemContainer(),
                               ItemContainer(ItemName=buf,
                                             IsItem = False,
                                             HasChildren = True))
            if len(lpath) == 1:
                for dec_node in dec_nodes:
                    # Only append if FANTYPE suites
                    # Returns /FANTYPE/FANID
                    if lpath[0] == dec_node[0]:
                        spath.add('%s%s%s%s' % (
                            bd,dec_node[0],
                            bd,dec_node[1]))
                for buf in spath:
                    IPH.append(ItemContainer(),
                               ItemContainer(ItemName=buf,
                                             IsItem = False,
                                             HasChildren = True))
            if len(lpath) == 2:
                for dec_node in dec_nodes:
                    # Only append if FANTYPE and NodeAddress suites
                    # Returns /FANTYPE/FANID/NODEADDRESS
                    if lpath[0] == dec_node[0] and \
                       lpath[1] == dec_node[1]:
                        spath.add('%s%s%s%s%s%s' % (
                            bd,dec_node[0],
                            bd,dec_node[1],
                            bd,dec_node[2]))
                for buf in spath:
                    # FIXME To be correct, the server should look for children, so that
                    # HasChildren is only set if the node really has datapoints
                    # This would require a nodeinfo
                    IPH.append(ItemContainer(),
                               ItemContainer(ItemName=buf,
                                             IsItem = False,
                                             HasChildren = True))
        if len(lpath) == 3:
            # The result is a nodelist
            # Returns /FANTYPE/FANID/NODEADDRESS/DPADDRESS
            for node in nodes[1:]:
                dec_node=ESD.DecodeESDAddress(node[0])
                IPH.append(ItemContainer(),
                           ItemContainer(ItemName='%s%s%s%s%s%s%s%s' % (
                               bd,dec_node[0],
                               bd,dec_node[1],
                               bd,dec_node[2],
                               bd,dec_node[3]),
                                         IsItem = False,
                                         HasChildren = True))
        if len(lpath) == 4:
            # The result is a DPInfoResult
            # Returns /FANTYPE/FANID/NODEADDRESS/DPADDRESS/ENCODING
            dec_node=ESD.DecodeESDAddress(nodes[0])
            encodings = nodes[2]
            for encoding in encodings:
                IPH.append(ItemContainer(),
                           ItemContainer(ItemName='%s%s%s%s%s%s%s%s%s%s' % (
                               bd,dec_node[0],
                               bd,dec_node[1],
                               bd,dec_node[2],
                               bd,dec_node[3],
                               bd,encoding),
                                         IsItem = True,
                                         HasChildren = False))
                
        return super(ESDProxy,self).Browse((IPH,inOptions,outOptions))
            
    
    def GetProperties(self,(IPH,inOptions,outOptions)):
        ''' Create OPC GetProperties data
        '''
        # Here all results will be stored
        self.prop_results = []
        dlist = []
        for seq,(inItem,outItem) in enumerate(IPH):
            # Store sequence for enabling assemblage later
            inItem.Sequence = seq
            d = self.ReadESDProperties(inItem,outItem)
            dlist.append(d)
        return defer.DeferredList(dlist).addCallback(self._cbGetProperties,(IPH,inOptions,outOptions))
    
    def ReadESDProperties(self,inItem,outItem):
        ''' Read Properties from ESD '''
        lpath = inItem.ItemName.strip('/').split(self.BrowseDelimiter)
        lpath.extend([None]*(5-len(lpath)))
        fantype,fanid,nodeaddress,dpaddress,encoding = lpath
        if (not fantype) or (not fanid) or (not nodeaddress):
            # Invalid address
            # outItem.ResultID = self.OPC_E_INVALIDITEMNAME
            self.prop_results.append((inItem.Sequence,inItem,outItem))
            return defer.succeed(None)
        elif (not dpaddress) and (not encoding):
            # Retrieve Node properties
            esd = ESD.SimpleClient(self.esd_host,self.esd_port)
            d = esd.NodeInfo('%s.%s!%s' % (fantype, fanid, nodeaddress))
            d.addCallback(self._cbReadESDPropertiesNode,inItem,outItem) 
            d.addErrback(self._errGetProperties,inItem,outItem,self.ESD_E_NODEINFO)
            return d
        else:
            # Retrieve Datapoint properties
            esd = ESD.SimpleClient(self.esd_host,self.esd_port)
            d = esd.DPInfo('%s.%s!%s@%s' % (fantype, fanid, dpaddress, nodeaddress))
            d.addCallback(self._cbReadESDPropertiesDP,inItem,outItem,encoding) 
            d.addErrback(self._errGetProperties,inItem,outItem,self.ESD_E_DPINFO)
            return d
        
    def _cbReadESDPropertiesNode(self,(NodeAddress,dp_num,nsid_str,opt1_str,opt2_str),
                                 inItem,outItem):
        ''' Handle result of ESD NodeInfo '''
        outItem.addProperty(OPCProperty(Name='description',Value=nsid_str))
        outItem.addProperty(OPCProperty(Name='NodeAddress',Value=NodeAddress))
        outItem.addProperty(OPCProperty(Name='dp_num',Value=dp_num))
        outItem.addProperty(OPCProperty(Name='opt1_str',Value=opt1_str))
        outItem.addProperty(OPCProperty(Name='opt2_str',Value=opt2_str))
        self.prop_results.append((inItem.Sequence,inItem,outItem))

    def _cbReadESDPropertiesDP(self,(DpAddress,DataType,SetOfEncodings,Access,dp_name,sid_str),
                               inItem,outItem,reqEncoding):
        ''' Handle result of ESD DPInfo '''
        outItem.addProperty(OPCProperty(Name='description',Value=dp_name))
        outItem.addProperty(OPCProperty(Name='DpAddress',Value=DpAddress))
        outItem.addProperty(OPCProperty(Name='ESDDataType',Value=DataType))
        outItem.addProperty(OPCProperty(Name='ESDSetOfEncodings',Value=':'.join(SetOfEncodings)))
        outItem.addProperty(OPCProperty(Name='sid_str',Value=sid_str))
        if reqEncoding:
            if reqEncoding in ('STRING','BINHEX','TIME'):
                outItem.addProperty(OPCProperty(Name='dataType',Value=QNameValue(NS_XSD, 'string')))
            elif reqEncoding == 'SCALARBIN':
                outItem.addProperty(OPCProperty(Name='dataType',Value=QNameValue(NS_XSD, 'float')))
            else:
                outItem.addProperty(OPCProperty(Name='dataType',ResultID=self.ESD_E_INVALIDENCODING,
                                                ErrorText='Invalid Encoding'))
            if Access == 'RW':
                outItem.addProperty(OPCProperty(Name='accessRights',Value='readWriteable'))
            elif Access == 'RO':
                outItem.addProperty(OPCProperty(Name='accessRights',Value='readable'))
            else:
                outItem.addProperty(OPCProperty(Name='accessRights',Value='unknown'))
        self.prop_results.append((inItem.Sequence,inItem,outItem))
    
    def _cbGetProperties(self,result,(IPH,inOptions,outOptions)):
        ''' Assemble IPH and return it '''
        # Sort results so that sequence is correct again
        self.prop_results.sort()
        rIPH = ItemPairHolder()
        for i,inItem,outItem in self.prop_results:
            rIPH.append(inItem,outItem)
        return super(ESDProxy,self).GetProperties((rIPH,
                                                   inOptions,
                                                   outOptions))
    def _errGetProperties(self, failure, inItem, outItem,esderr):
        ''' Fill errorneous property '''
        outItem.ResultID = esderr
        outItem.ErrorText = str(failure.value.args)
        self.prop_results.append((inItem.Sequence,inItem,outItem))


if __name__ == '__main__':
    # Start the basic server
    from twisted.web import resource, server
    xdasrv = ESDProxy(http_log_fn = 'http.log')
    root = resource.Resource()
    root.putChild('',xdasrv)
    site = server.Site(root)
    reactor.listenTCP(8000, site)
    
    def PrintArgs(result,cmd,stop=False):
        print cmd,':',result
        if stop: 
            reactor.callLater(2,reactor.stop)
    def PrintErr(failure,cmd,stop=False):
        print cmd,':',failure.value
        if stop: 
            reactor.callLater(2,reactor.stop)

    from PyOPC.TWXDAClient import TWXDAClient
    from PyOPC.OPCContainers import *
    URL = "http://127.0.0.1:8000/"
    xda = TWXDAClient(OPCServerAddress = URL)
    
    #xda.twBrowse().addCallback(PrintArgs,'Browse').addErrback(PrintErr,'Browse')
    #xda.twBrowse(ItemName='/LON').addCallback(PrintArgs,'Browse').addErrback(PrintErr,'Browse')
    #xda.twBrowse(ItemName='/LON/GATE1').addCallback(PrintArgs,'Browse').addErrback(PrintErr,'Browse')
    #xda.twBrowse(ItemName='/LON/GATE1/01:02:03:04:05:06').addCallback(PrintArgs,'Browse',True).addErrback(PrintErr,'Browse',True)
    #xda.twBrowse(ItemName='/LON/GATE1/01:02:03:04:05:06/11').addCallback(PrintArgs,'Browse',True).addErrback(PrintErr,'Browse',True)
    #xda.twBrowse(ItemName='/LON/GATE1/01:02:03:04:05:06/11/asdf').addCallback(PrintArgs,'Browse',True).addErrback(PrintErr,'Browse',True)
    #xda.twGetProperties((ItemContainer(ItemName = '/LON/GATE1/01:02:03:04:05:06/11'),
    #                   ItemContainer(ItemName = '/LON/GATE1/01:02:03:04:05:06/12')),
    #                    ReturnErrorText=True).addCallback(\
    #                       PrintArgs,'GetProperties',True).addErrback(\
    #                           PrintErr,'GetProperties',True)
    #xda.twRead((ItemContainer(ItemName = '/LON/GATE1/01:02:03:04:05:06/11/BINHEX'),
    #            ItemContainer(ItemName = '/LON/GATE1/01:02:03:04:05:06/12/STRING')),
    #           ReturnErrorText=True).addCallback(\
    #               PrintArgs,'Read',True).addErrback(\
    #                   PrintErr,'Read',True)
    #xda.twWrite((ItemContainer(ItemName = '/LON/GATE1/01:02:03:04:05:06/11/SCALARBIN', Value = 12.2),
    #            ItemContainer(ItemName = '/LON/GATE1/01:02:03:04:05:06/12/STRING', Value = "31. 5")),
    #           ReturnErrorText=True).addCallback(\
    #               PrintArgs,'Write',True).addErrback(\
    #                   PrintErr,'Write',True)

    
    reactor.run()
