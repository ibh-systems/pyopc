'''OPC XMLDA 1.0 Server module '''

import string,random,time,sys,datetime,copy
#from datetime import datetime
from twisted.web import resource, server, http
from twisted.internet import reactor, defer, threads, task
from twisted.python import log
from OPCBuffer import OPCBuffer
# Should already be imported
import xml.dom.minidom


# Import ZSI generated code
import OpcXmlDaSrv_services

# Import OPC XMLDA messages
from OPCContainers import *

class ItemPairHolder(object):
    ''' Class that holds an in and an out ItemContainer '''


    def __init__(self):
        self.inIClist  = []
        self.outIClist = []

    def __iter__(self):
        return iter(zip(self.inIClist,self.outIClist))

    def append(self,inItem = None, outItem = None):
        ''' Appends Items to ItemPairHolder '''
        self.inIClist.append(inItem)
        self.outIClist.append(outItem)

class ItemCache(object):
    ''' Class that caches items in a dictionary '''

    def __init__(self,MaxAge=1000):
        # Initialize Cache
        self._cache = {}
        # Default Maximum Age - used for read operations
        self.MaxAge = MaxAge # in ms

    def cache(self,Item):
        ''' Write Item to cache and return old cache entry, if available '''
        # Store the time the item was cached in Item.CacheTimestamp
        Item.CacheTimestamp=time.time()
        key = mkItemKey(Item)
        if key:
            # Retrieve old cached entry
            oldItem = self._cache.get(key,None)
            # Store Item in cache, copy it first
            self._cache[key] = copy.copy(Item)
            return oldItem
        else:
            return None

    def setread(self,reqItem):
        ''' Set IsRead flag for given Item in cache '''
        cachedItem = self._cache.get(mkItemKey(reqItem),None)
        if cachedItem:
            cachedItem.IsRead = True

    def read(self,reqItem,MaxAge=None):
        ''' Read Item from cache, return Item or None if not available '''
        if MaxAge == None:
            MaxAge = self.MaxAge
        if reqItem.MaxAge != None:
            MaxAge = reqItem.MaxAge
        # Retrieve cached Item
        cachedItem = self._cache.get(mkItemKey(reqItem),None)
        if cachedItem:
            # Check Age
            if MaxAge < 0:
                # Always return cached item if MyxAge is negativ
                return cachedItem
            # FIXME MaxAge should be compared to Item.Timestamp if available
            # This should be preferred to Item.CacheTimestamp
            if ((time.time() - cachedItem.CacheTimestamp) * 1000) > MaxAge:
                # Cache entry is too old
                return None
            else:
                return cachedItem
        else:
            # There was no such Cache entry
            return None
            
    def pop(self,Item):
        ''' Pop Item from cache '''
        return self._cache.pop(mkItemKey(Item),None)

    def delete(self,Item):
        ''' Delete Item from cache '''
        self.pop(Item)
        
    def flush(self,Age):
        ''' Delete all Items where Item.CacheTimestamp - time.time() > Age '''
        for key,Item in self._cache.items():
            if ((time.time() - Item.CacheTimestamp) * 1000) > Age:
                del self._cache[key]

class Subscription(object):
    ''' An object that holds all necessary information for a subscription '''

    def __init__(self,IPH,inOptions,outOptions):
        ''' Initialize the Subscription object '''
        self.IPH = IPH
        self.inOptions = inOptions
        self.outOptions = outOptions
        # Dict of polling clients
        self.PollDeferDict = {}
        # Dict of currently polling clients
        self.PollClientDict = {}
        # List of Items: Tuple of (cachedItem,ReadFunc,Loop)
        self.SubItems = []
        # Create a new Item Cache
        # Initialize with MaxAge = -1 so that value are always returned
        self.Cache = ItemCache(-1)

class XDAServer(resource.Resource, OPCOperation):
    ''' Class that implements an XMLDA OPC Server '''

    # Logging default filenames
    access_log_fn='access.log'
    error_log_fn='error.log'
    http_log_fn=''
    # Logging handlers - if set to 0, no logging is done
    access_log_fd = 0
    error_log_fd = 0
    http_log_fd = 0

    # Boolean sinalling if server is unittesting
    # in this case some functions will report status and moreover
    # callback twisted deferreds
    UTEST = False

    # Attributes for Status
    VendorInfo = 'PyOPC XMLDA Server'
    SupportedInterfaceVersions = ('XML_DA_Version_1_0',)
    ServerState = 'running'
    # ZSI-TIMEFIX
    # StartTime = datetime.datetime.now()
    StartTime = time.time()
    ProductVersion = '0.01.1.00'

    # Attribute for Caching
    # Enable/Disable automatic Item Caching
    AutoItemCache = True
    # Purge Cache entry if an item is written, so that clients
    # never get back items that are outdated due to writes from this server
    WritePurgeCache  = True
    # Default MaxAge which may be used for read operations
    DefaultMaxAge = 1000

    # The buffer size where sampled values are stored for subscriptions
    BufferSize = 100

    # Specify if the XML parsing should be done in a seperate thread
    ThreadedParsing = False
    # How many concurrent threads are allowed for this server
    ThreadPoolSize = 5

    # Default for the SubscriptionPingRate after that the Subscr. is cancelled
    SubscriptionPingRate = 10000 # in milliseconds -> 10 Seconds
    MaxPingRate = 86400000 # One Day

    # Maximum Sampling rate that the server accepts
    MaxSamplingRate = 100 # (in milliseconds) -> 0.1 Second

    ########### Property related options ###############
    # If true, properties are accessible as items - in the
    # Hierarchy below the item, delimited by "PropertyDelimiter"
    # Example: /path/to/item1.property1
    # These properties can then be read/written, which will
    # issue GetProperties/WriteProperties
    # FIXME: Not fully implemented by now
    # However, if set to True, ItemName/ItemPath will be automatically
    # filled in
    MkItemProperties = True
    PropertyDelimiter = '.Property_'
    # Should the properties "value", "quality", "timestamp" and "scanRate"
    # be handled automatically?
    HandleProperty_value = True
    HandleProperty_quality = True
    HandleProperty_timestamp = True
    # "scanRate" will be set to MaxSamplingRate
    HandleProperty_scanRate = True

    def __init__(self,*kl,**kd):
        ''' Initialize the log files and call super-inits'''
        # Initalize caches and subscriptions and buffers
        self.ReadCache = ItemCache(MaxAge=self.DefaultMaxAge)
        self.SubscriptionBuffer = OPCBuffer(self.BufferSize)
        # Subscription Dictionary
        # Key is the ServerSubHandle
        self.SubscriptionDict = {}

        for n, v in kd.iteritems():
            setattr(self, n, v)

        # Open Access/Error Log
        if self.access_log_fn:
            # open access log
            self.access_log_fd = file(self.access_log_fn,'a+',0)
            
        if self.error_log_fn:
            # open error log
            self.error_log_fd = file(self.error_log_fn,'a+',0)
                
        if self.http_log_fn:
            # open http transfer log
            self.http_log_fd = file(self.http_log_fn,'a+',0)

        super(XDAServer, self).__init__()


    def log(self,logtype,buf):
        ''' Log errors '''

        logfd = getattr(self,'%s_log_fd' % logtype)

        if logfd:
            logfd.write('%s %s\n' % \
                        (time.strftime('%b %d %H:%M:%S'),
                        buf))

    def access_log(self,buf):
        ''' Log server access '''
        self.log('access',buf)
        
    def error_log(self,buf):
        ''' Log server errors '''
        self.log('error',buf)

    def http_log(self,prefix,header_dict,content):
        ''' Log all HTTP request/response messages '''

        # make sure HTTP logging is enabled
        if self.http_log_fd:
            http_header = '\n'.join('%s: %s' % i for i in header_dict.items())
            
            # do a little pretty printing

            pretty_content = xml.dom.minidom.parseString(content).toprettyxml()
            buf = '%s\n%s\n\n%s' % (prefix,http_header,pretty_content)
            self.log('http',buf)

    def revSamplingRate(self,reqSamplingRate):
        ''' Make an appropriate sampling rate (input ms, output seconds)
        This may be overridden for custom calculations of the sampling rate '''
        
        if reqSamplingRate == None:
            return False,float(self.MaxSamplingRate) / 1000.0
        else:
            rate = float(reqSamplingRate)
            if rate < self.MaxSamplingRate:
                return True,float(self.MaxSamplingRate) / 1000.0
            else:
                return False,float(rate)/1000.0

    def HasChanged(self,oldItem,newItem):
        ''' Check if newItem is "interesting", which means that
        the new value is less than newItem.Deadband (specified in percent
        of the old Value) or quality has changed.
        Returns True if it is interesting.
        '''

        # Check if certain ItemContainer attributes are equal
        for attr in ('ItemName',
                     'ItemPath',
                     'ResultID',
                     'QualityField',
                     'LimitField',
                     'VendorField',
                     'ValueTypeQualifier'):
            newVal = getattr(newItem,attr)
            oldVal = getattr(oldItem,attr)
            if oldVal or newVal:
                # '', [], None are handled as "equal"
                if oldVal != newVal:
                    # Some attribute has changed
                    return True

        # Both values must be of same type (unless int/long/floats)
        if not isinstance(newItem.Value,(int,long,float)) and \
           not isinstance(oldItem.Value,(int,long,float)):
            if type(newItem.Value) != type(oldItem.Value):
                return True

        if not newItem.Deadband:
            # There is no Deadband or it is 0
            return newItem.Value != oldItem.Value

        # Now do the Deadband checks
        if isinstance(newItem.Value,(int,long,float)):
            # Deadband checking for Numbers
            percent = oldItem.Value * (newItem.Deadband/100.0)
            return oldItem.Value + percent < newItem.Value
        else:
            # No Deadband for all other instances
            return newItem.Value != oldItem.Value
            

    def handle_failure(self,failure,request):
        ''' Handle various errors from previous callbacks '''
        request.setResponseCode(http.INTERNAL_SERVER_ERROR)

        if failure.check(ZSI.ParseException,ZSI.EvaluateException):
            f = ZSI.FaultFromZSIException(failure.value)
            buf = str(f.AsSOAP())
        elif failure.check(OPCServerError):
            f = ZSI.Fault(failure.value.code,
                          failure.value.string,
                          detail=failure.value.detail)
            buf = str(f.AsSOAP())
        else:
            # Catch all other (possible program) exceptions
            self.error_log('%s\n%s' % (failure.value,
                                       failure.getTraceback()))
            f = ZSI.FaultFromException(failure.value,
                                       False,
                                       tb=failure.getTraceback())
            buf = str(f.AsSOAP())

        # Content-length
        request.setHeader('content-length',len(buf))
        # Log the error
        self.http_log('------------ Response ------------',
                      request.headers,
                      buf)
        # Now write the error and finish
        # Write SOAP message
        request.write(buf)
        # Finish the whole operation
        request.finish()

    def parse_stage1(self,soap_content):
        ''' Create ParsedSoap (possibly in a thread)'''
        if self.ThreadedParsing:
            d = threads.deferToThread(ZSI.ParsedSoap,soap_content)
            return d
        else:
            return ZSI.ParsedSoap(soap_content)

    def parse_stage2(self,ps,tc_in):
        ''' Parse ParsedSoap into typecodes '''
        tc_in =  ps.Parse(tc_in.typecode)
        
        inIClist,inOptions = self.read_tc(tc_in)

        outOptions = {}
        IPH = ItemPairHolder()
        for inItem in inIClist:
            IPH.append(inItem = inItem, outItem = ItemContainer())

        return IPH, inOptions, outOptions

    def serialize_stage1(self,(IPH,inOptions,outOptions),tc_out):
        ''' Fill typecode '''
        self.fill_tc(tc_out, IPH.outIClist, outOptions)
        return tc_out


    def serialize_stage2(self, tc_out, request):
        ''' Serialize typecode and write SOAP message '''
        # serialize typecode
        SOAPMessage = ZSI.SoapWriter().serialize(tc_out,unique=True)

        # Now write the SOAP message
        buf = str(SOAPMessage)
        request.setHeader('content-length',len(buf))
        self.http_log('------------ Response ------------',
                      request.headers,
                      buf)

        # Write SOAP message
        request.write(buf)
        # Finish the whole operation
        request.finish()


    ################# Helper Methods for OPC Operations ###########

    def split_IPH(self,IPH):
        ''' Split IPH into an non-error IPH and an error IPH
        '''
        IPH_OK = ItemPairHolder()
        IPH_ERR = ItemPairHolder()
        i=0
        for inItem,outItem in IPH:
            # Give the item a Sequence number, so that they can
            # be assembled later
            inItem.Sequence=i
            i += 1
            if IsCritical(outItem.ResultID):
                IPH_ERR.append(inItem,outItem)
            else:
                IPH_OK.append(inItem,outItem)
        return IPH_OK,IPH_ERR

    def join_IPH(self,IPH_OK,IPH_ERR):
        ''' Join non-error/error IPHs into one IPH while maintaining the
        sequence.
        '''
        Item_List = []
        # Add all non-error Items
        for inItem,outItem in IPH_OK:
            Item_List.append((inItem.Sequence,inItem,outItem))
        # Add all error Items
        for inItem,outItem in IPH_ERR:
            Item_List.append((inItem.Sequence,inItem,outItem))
        # Now sort the list after the sequence
        Item_List.sort()

        IPH = ItemPairHolder()
        for item in Item_List:
            IPH.append(item[1],item[2])
        return IPH

    def AssembleIPH(self,(IPH_OK,inOptions,outOptions),IPH_ERR):
        ''' Just a wrapper for join_IPH '''
        IPH = self.join_IPH(IPH_OK,IPH_ERR)
        return IPH,inOptions,outOptions
            
    def ReviseLocale(self,inOptions,outOptions):
        ''' Check if requested Locale is available - if
        not return the first item in self.SupportedLocaleIDs
        If self.SupportedLocaleID == None, return empty string'''

        ReqLoc = inOptions.get('LocaleID',None)

        if ReqLoc:
            SupLocs =  getattr(self,'SupportedLocaleIDs', None)
            if SupLocs in (None, []):
                outOptions['RevisedLocaleID'] = ''
            else:
                if ReqLoc not in SupLocs:
                    outOptions['RevisedLocaleID'] = SupLocs[0]

    def FillReplyBase(self,(IPH,inOptions,outOptions)):
        ''' Fill some options which form the OPC "ReplyBase" '''

        outOptions['RcvTime'] = self.rec_time

        crh = inOptions.get('ClientRequestHandle',None)
        if crh != None:
            outOptions['ClientRequestHandle'] = crh
        
        self.ReviseLocale(inOptions,outOptions)
        self.setfromattr('ServerState', outOptions)

        return IPH,inOptions,outOptions

    def FixOutValues(self,(IPH,inOptions,outOptions)):
        ''' Fill/Fix various Options '''
        for inItem,outItem in IPH:
            if outItem.IsEmpty:
                # This item has not been filled by any inherited
                # operation, hence fill it out with an error
                outItem.ResultID = self.PYO_E_EMPTYITEM
                outItem.ErrorText = 'The OPC Item contains no data'
                
            # Now set/fix various item attributes according to
            # the request options
            # Fix/Fill ErrorText
            if inOptions.get('ReturnErrorText',None) == False:
                outItem.ErrorText = None
            else:
                if outItem.ErrorText == None:
                    # If ErrorText is requested and there is none, set it to ''
                    outItem.ErrorText = ''
            # Fix/Fill DiagnosticInfo
            if inOptions.get('ReturnDiagnosticInfo',None) in (False,None):
                outItem.DiagnosticInfo = None
            else:
                if outItem.DiagnosticInfo == None:
                    # If DiagInfo is requested and there is none, set it to ''
                    outItem.DiagnosticInfo = ''
            # Fix/Fill Timestamp
            if inOptions.get('ReturnItemTime',None) in (False,None):
                outItem.Timestamp = None
            else:
                if outItem.Timestamp == None:
                    # If there is no Timestamp, set it to now
                    outItem.Timestamp = datetime.datetime.now()
            # Fix/Fill ItemPath
            if inOptions.get('ReturnItemPath',None) in (False,None):
                outItem.ItemPath = None
            else:
                if outItem.ItemPath == None:
                    # If there is no ItemPath, set it to inItem.ItemPath or ''
                    if inItem.ItemPath:
                        outItem.ItemPath = inItem.ItemPath
                    else:
                        outItem.ItemPath = ''
            # Fix/Fill ItemName
            if inOptions.get('ReturnItemName',None) in (False,None):
                outItem.ItemName = None
            else:
                if outItem.ItemName == None:
                    # If there is no ItemName, set it to inItem.ItemName or ''
                    if inItem.ItemName:
                        outItem.ItemName = inItem.ItemName
                    else:
                        outItem.ItemName = ''
            
            # Set ClientItemHandle - always copy from in to out
            outItem.ClientItemHandle = inItem.ClientItemHandle

        # Set ReplyTime if RcvTime is set and ReplyTime is not already there
        # This way ReplyTime may be overridden by custom code
        # Moreover it is assumed that if RcvTime is not set,
        # ReplyTime should also not be set automatically
        if not outOptions.has_key('ReplyTime'):
            outOptions['ReplyTime'] = datetime.datetime.now()

        return IPH,inOptions,outOptions
    


    def addSubscription(self,(IPH,inOptions,outOptions),sub_inOptions):
        ''' Add a subscription to the Subscription Dictionary '''

        # Create a unique ServerSubHandle
        while True:
            i = random.randint(1000000,9999999)
            ServerSubHandle = 'SSubHandle_%s' % i
            if not self.SubscriptionDict.has_key(ServerSubHandle):
                break
        if self.UTEST:
            msg = (time.time(),
                   'addSub',
                   None)

            self.UTEST_SUBMSGS[ServerSubHandle] = [msg]
        # Append it to the outOptions
        outOptions['ServerSubHandle'] = ServerSubHandle

        # Transfer some options from Option to Item level
        for inItem,outItem in IPH:
            self.setfrom_self_or_dict(inOptions,'Deadband',inItem)
            self.setfrom_self_or_dict(inOptions,'RequestedSamplingRate',inItem)
            self.setfrom_self_or_dict(inOptions,'EnableBuffering',inItem)

        # Create Subscription object
        s = Subscription(IPH,inOptions,outOptions)
        s.ServerSubHandle = ServerSubHandle

        ReturnValuesOnReply = inOptions.get('ReturnValuesOnReply',None)

        for inItem, outItem in IPH:
            # Identify some values
            if not IsCritical(outItem.ResultID):
                # Only subscribe to items that have no errors
                # Cache item
                if ReturnValuesOnReply:
                    outItem.IsRead = True
                else:
                    outItem.IsRead = False
                s.Cache.cache(outItem)
                # Now a nested read function has to be created.
                # Create a IPH for the read function
                readIPH = ItemPairHolder()
                # Fill the rIPH with only one item
                readIPH.append(copy.copy(inItem),ItemContainer())

                # A closure that serves as the read function
                # ATTENTION: This closure does not duplicate any
                # objects which are referenced, it will get references
                # from the local namespace. Therefore the addressed
                # items in the for-loop must be transferred to the
                # local namespace in the closure.
                # Others such as "s or outOptions" may be referenced
                # directly
                def SampleItem(readIPH=readIPH):
                    ''' Sample an OPC Item '''
                    # For unit testing
                    if self.UTEST:
                        msg = (time.time(),
                               'LoopingRead',
                               None)
                        self.UTEST_SUBMSGS[ServerSubHandle].append(msg)
                        self.UTEST_MSGS.append(msg)
                    # The server's Read operation
                    d = defer.maybeDeferred(self.Read,
                                            (readIPH,inOptions,outOptions))
                    # Fill/Fix various options and the IPH
                    d.addCallback(self.FixOutValues)
                    # The function that buffers/caches the values
                    d.addCallback(HandleSampledItem)
                    # Add default errback
                    d.addErrback(log.err)

                    return d

                def HandleSampledItem((b_IPH,b_inOptions,b_outOptions)):
                    ''' Cache/Buffer values from the read operation '''
                    for readreqItem,readresItem in b_IPH:
                        # Copy the result of the read to break possible
                        # conflicts with references from the ReadCache
                        cachedItem = s.Cache.read(readreqItem)
                        # Check if the new item differs in some way
                        if self.HasChanged(cachedItem,readresItem):
                            # Value has changed: cache it
                            if readreqItem.EnableBuffering and \
                                   cachedItem.IsRead != True:
                                # Buffer only if the old item was never read
                                # and buffering is enabled
                                key = s.ServerSubHandle+mkItemKey(cachedItem)
                                self.SubscriptionBuffer.store(key, cachedItem)
                            else:
                                # In case there was an old cached item,
                                # denote that data was lost
                                if cachedItem and \
                                       cachedItem.IsRead != True:
                                    readresItem.ResultID=\
                                            self.OPC_S_DATAQUEUEOVERFLOW
                            # Now cache new entry, overwriting the old one
                            s.Cache.cache(readresItem)
                            # Now callback all waiting Polls
                            # Make a backup copy of PollDeferDict
                            d = dict(s.PollDeferDict)
                            # Cleanup all Polls
                            for v in s.PollDeferDict.values():
                                SubPollCleanup=v[1]
                                SubPollCleanup()
                            # Now callback all WaitDeferreds
                            # with WaitParams
                            for WaitDeferred,v in d.items():
                                CallbackParams = v[0]
                                WaitDeferred.callback(CallbackParams)
                        else:
                            # No cache-updating/buffering, update timestamp
                            cachedItem.Timestamp = readresItem.Timestamp
                
                # Create the periodic read function
                l = task.LoopingCall(SampleItem)
                s.SubItems.append((inItem,l))
                # Start the periodic read function
                revised,rate = self.revSamplingRate(inItem.\
                                                    RequestedSamplingRate)
                if revised:
                    outItem.RequestedSamplingRate = rate
                    
                if self.UTEST:
                    msg = (time.time(),'LoopStart',rate)
                    self.UTEST_SUBMSGS[ServerSubHandle].append(msg)
                    self.UTEST_MSGS.append(msg)
                l.start(rate,now=False)


        # Handle The automatic unsubscription
        if s.SubItems:
            # Only if there is something to subscribe!
            if inOptions.has_key('SubscriptionPingRate'):
                s.SubscriptionPingRate = inOptions['SubscriptionPingRate']
                # Must not be greater than MaxPingRate
                # This way hanging subscriptions due to faulty subscriptions
                # are prevented
                if s.SubscriptionPingRate > self.MaxPingRate:
                    s.SubscriptionPingRate = self.MaxPingRate
            else:
                # Default/Class value instead
                s.SubscriptionPingRate = self.SubscriptionPingRate

            def SubCancel(ServerSubHandle=ServerSubHandle):
                self.SubscriptionCancel(\
                    (ItemPairHolder(),
                     {'ServerSubHandle':ServerSubHandle,
                      'ClientRequestHandle':\
                      inOptions.get('ClientRequestHandle',None)},
                     {}))
                
            s.Cancel = SubCancel
            s.ClCmdID = reactor.callLater(s.SubscriptionPingRate/1000.0,
                                          s.Cancel)

            # Now append this Subscription object to the dictionary
            self.SubscriptionDict[ServerSubHandle] = s
        else:
            # There was nothing to subscribe, hence there should be no
            # ServerSubHandle
            del outOptions['ServerSubHandle']
            
        # Handle ReturnValuesOnReply
        if ReturnValuesOnReply:
            return IPH,sub_inOptions,outOptions
        else:
            # Return only errorneous items
            errIPH = ItemPairHolder()
            for inItem,outItem in IPH:
                if IsCritical(outItem.ResultID):
                    errIPH.append(inItem,outItem)
            return errIPH,sub_inOptions,outOptions

            
    ######################### OPC Operations #######################

    def GetStatus(self, (IPH,inOptions,outOptions)):
        ''' Create OPC Status data
        Set ServerState to running,
        '''
        return IPH,inOptions,outOptions
   
    def CachedRead(self,(IPH,inOptions,outOptions)):
        ''' Try to read data from the cache and call
        Read if no appropriate cached data is available
        '''
        IPH_CACHE = ItemPairHolder()
        IPH_READ = ItemPairHolder()
        i = 0
        for inItem,outItem in IPH:
            # Give the item a Sequence number so that it can be
            # assembled later
            inItem.Sequence=i
            i += 1
            # Set MaxAge on an ItemLevel
            global_MaxAge = inOptions.get('MaxAge',None)
            if inItem.MaxAge == None:
                inItem.MaxAge = global_MaxAge
            cacheItem =  self.ReadCache.read(inItem)
            if cacheItem:
                IPH_CACHE.append(inItem,cacheItem)
            else:
                IPH_READ.append(inItem,outItem)

        # Read the remaining items that could not be retrieved from the cache
        d = defer.maybeDeferred(self.Read,
                                (IPH_READ,inOptions,outOptions))
        # Join the OK and Errorneous items again
        d.addCallback(self.AssembleIPH,IPH_CACHE)
        return d

    def Read(self,(IPH,inOptions,outOptions)):
        ''' Create OPC Read data
        '''
        if self.AutoItemCache:
            # Store Items in cache
            for inItem,outItem in IPH:
                if not IsCritical(outItem.ResultID) and \
                       outItem.IsEmpty == False:
                    # Only store non-error Items
                    # Set ItemName/ItemPath from inItem
                    cacheItem = copy.copy(outItem)
                    cacheItem.ItemName = inItem.ItemName
                    cacheItem.ItemPath = inItem.ItemPath
                    # Do not store the ClientItemHandle
                    cacheItem.ClientItemHandle=None
                    self.ReadCache.cache(cacheItem)
            
        return IPH,inOptions,outOptions
        
    def Write(self,(IPH,inOptions,outOptions)):
        ''' Create OPC Write data
        '''
        if self.AutoItemCache and self.WritePurgeCache:
            # Purge all (successfully) written entries from the cache
            for inItem,outItem in IPH:
                if not IsCritical(outItem.ResultID):
                    self.ReadCache.delete(inItem)
            
        if inOptions.get('ReturnValuesOnReply',None) == True:
            # Split IPH into non-error and error IPHs
            IPH_OK,IPH_ERR = self.split_IPH(IPH)
            # Call the Read operation
            d = defer.maybeDeferred(self.Read,
                                    (IPH_OK,inOptions,outOptions))
            # Join the OK and Errorneous items again
            d.addCallback(self.AssembleIPH,IPH_ERR)
            # Fill/Fix various options and the IPH
            d.addCallback(self.FixOutValues)
            # Return this deferred
            return d
        else:
            # Return the IPH without values, however make it "non-Empty"
            for inItem,outItem in IPH:
                outItem.IsEmpty = False
            return IPH,inOptions,outOptions

    def Subscribe(self,(IPH,sub_inOptions,outOptions)):
        ''' Create OPC Subscribe data
        '''
        # Set specific options so that certain Item properties are
        # read
        inOptions = dict(sub_inOptions)
        inOptions['ReturnErrorText'] = True
        inOptions['ReturnDiagnosticInfo'] = True
        inOptions['ReturnItemTime'] = True
        inOptions['ReturnItemPath'] = True
        inOptions['ReturnItemName'] = True
        # First read all items
        d = defer.maybeDeferred(self.Read,
                                (IPH,inOptions,outOptions))
        # Fill/Fix various options and the IPH
        d.addCallback(self.FixOutValues)
        # Add these values to the subscription
        d.addCallback(self.addSubscription,sub_inOptions)
        # Fill/Fix various options and the IPH
        # This has to be done again as ItemNames/Times are present
        # as they must be read into the subscription cache
        # which may not be requested by the client
        d.addCallback(self.FixOutValues)
        # Return this deferred
        return d

    def SubscriptionPolledRefresh(self,(IPH,inOptions,outOptions)):
        ''' Create OPC SubscriptionPolledRefresh data
        '''

        # Check for valid subscriptions
        subList = []
        failedHandles = []
        handles = inOptions.get('ServerSubHandles',None)
        if handles:
            for handle in handles:
                s = self.SubscriptionDict.get(handle,None)
                if s:
                    subList.append(s)
                else:
                    failedHandles.append(handle)
                    
        outOptions['InvalidServerSubHandles'] = failedHandles

        if subList == []:
            # No valid subscriptions, hence return
            return IPH,inOptions,outOptions

        # SubscriptionPolledRequests are "blocking", meaning
        # that only one may be issued per Subscription object
        for s in subList:
            if s.PollClientDict != {}:
                raise OPCServerError(self.OPC_E_BUSY,
                                     'Only one poll per subscription allowed!')

        # HoldTime is in absolute time
        HoldTime = inOptions.get('HoldTime',None)
        if (HoldTime == None) or (not isinstance(HoldTime,datetime.datetime)):
            HoldTime = 0
        else:
            # Calculate relative HoldTime
            now = datetime.datetime.now()
            if now > HoldTime:
                # No HoldTime
                HoldTime = 0
            else:
                tdelta = HoldTime - now
                # Convert HoldTime to Seconds
                HoldTime = float(tdelta.seconds) + \
                           (float(tdelta.microseconds) / 1000000.0)
        WaitTime = inOptions.get('WaitTime',None)
        if WaitTime == None:
            WaitTime = 0
        else:
            # Convert from microseconds to seconds
            WaitTime = WaitTime/1000.0

        # Calculate the PollId for the SPR
        PollId=('Poll-%s_%s') % (time.time(),random.randint(1000,9999))
        for s in subList:
            # Denote that the subscription is polled via PollClientDict
            s.PollClientDict[PollId] = False
            # Cancel all pending unsubscriptions and add this poll
            # To the PollClientDict to denote that no one should start
            # the auto-unsub again until the poll has completed
            if getattr(s,'ClCmdID',None):
                if s.ClCmdID.active():
                    s.ClCmdID.cancel()
            
        # Create a deferred
        PollDeferred = defer.Deferred()
        # Wait for Value Changes
        if WaitTime and not inOptions.get('ReturnAllItems',None):
            WaitDeferred = defer.Deferred()
            PollDeferred.addCallback(self.PollWait,WaitTime,WaitDeferred)
            PollDeferred.addCallback(self.PollItems,WaitDeferred)
        else:
            PollDeferred.addCallback(self.PollItems,None)
        # Fire deferred after HoldTime which is set to '0' if it is None
        reactor.callLater(HoldTime,PollDeferred.callback,
                          (IPH,inOptions,outOptions,
                           PollId,subList,False))
        return PollDeferred

    def PollWait(self,(IPH,inOptions,outOptions,
                       PollId,subList,DelWaitDeferreds),
                 WaitTime,WaitDeferred):
        ''' Wait for value changes or a specified time '''
        # Check if a value has changed within HoldTime
        for s in subList:
            for SubItem,LoopingCall in s.SubItems:
                item = s.Cache.read(SubItem)
                if not item.IsRead:
                    return ((IPH,inOptions,outOptions,
                             PollId,subList,False))

        # Add Deferred to all subscription objects so that it may be
        # fired for a sampling read - only the key is of interest        
        WaitCancel=reactor.callLater(WaitTime,WaitDeferred.callback,
                                     (IPH,inOptions,outOptions,
                                      PollId,subList,True))

        def SubPollCleanup():
            ''' Cleanup function for HandleSampledItem() '''
            # First cancel all possible WaitCancels
            if WaitCancel.active():
                # Function could also be called when WaitCancel is already
                # canceled
                WaitCancel.cancel()
            # Now delete all deferreds of this Poll from all
            # Subscriptions in subList
            for s in subList:
                s.PollDeferDict.pop(WaitDeferred)

        # Now add the WaitDeferred including the Cleanup to the
        # PollDeferDict in all subscriptions which are polled
        CallbackParams = ((IPH,inOptions,outOptions,PollId,subList,False))

        for s in subList:
            s.PollDeferDict[WaitDeferred] = (CallbackParams,SubPollCleanup)

        return WaitDeferred
        

    def PollItems(self,(IPH,inOptions,outOptions,
                        PollId,subList,DelWaitDeferreds),
                  WaitDeferred):
        ''' Read changed values '''
        if DelWaitDeferreds and WaitDeferred != None:
            # The WaitDeferreds have to be deleted manually
            for s in subList:
                s.PollDeferDict.pop(WaitDeferred,None)
        else:
            # The deferred was fired from HandleSampledItem()
            # Hence a value has changed. HandleSampledItem() already
            # deleted all possible deferreds and WaitCancel()
            pass       # Nothing to do

        # Read all changed values from SubscriptionCache
        # and from Buffer
        for s in subList:
            for SubItem,LoopingCall in s.SubItems:
                citem = s.Cache.read(SubItem)
                if not citem.IsRead or inOptions.get('ReturnAllItems',None):
                    # This item has changed
                    # Denote that the item has been read
                    s.Cache.setread(SubItem)
                    if SubItem.EnableBuffering == True:
                        key = s.ServerSubHandle + mkItemKey(SubItem)
                        # Append all buffered items, oldest first
                        islost,buf_items=self.SubscriptionBuffer.retrieve(key)
                        for buf_item in buf_items:
                            if islost:
                                # Denote that recorded items were lost
                                buf_item.ResultID=self.OPC_S_DATAQUEUEOVERFLOW
                                outOptions['DataBufferOverflow'] = True
                            # Now append this item
                            IPH.append(SubItem,buf_item)
                        if outOptions.get('DataBufferOverflow',None):
                            # Also tell the cached item that a
                            # buffer overflow has occurred
                            citem.ResultID = self.OPC_S_DATAQUEUEOVERFLOW
                    else:
                        # Now append the changed item
                        # Denote that a buffer overflow occurred
                        if citem.ResultID == self.OPC_S_DATAQUEUEOVERFLOW:
                            outOptions['DataBufferOverflow'] = True
                    # Now - after buffered data - append the cached Item
                    IPH.append(SubItem,citem)
        
        # Setup a delayed calls to the SubscriptionCancel
        for s in subList:
            # Delete own Polling ID
            del s.PollClientDict[PollId]
            # Only create a cancel method if no PollingRequests are active
            if s.PollClientDict == {}:
                s.ClCmdID = reactor.callLater(s.SubscriptionPingRate/1000.0,
                                              s.Cancel)

        return IPH,inOptions,outOptions

    def SubscriptionCancel(self,(IPH,inOptions,outOptions)):
        ''' Create OPC SubscriptionCancel data
        '''
        ServerSubHandle = inOptions.get('ServerSubHandle',None)
        if ServerSubHandle == None:
            # There is no handle in the message, so return
            return IPH,inOptions,outOptions
            
        s = self.SubscriptionDict.get(ServerSubHandle,None)
        if s == None:
            # There is no such subscription in the server, so return
            return IPH,inOptions,outOptions

        # Now actually cancel the subscription
        # First stop the timeout unless it has expired (inactive)
        if s.ClCmdID.active():
            s.ClCmdID.cancel()
        # Stop periodic reading (sampling)
        for sub in s.SubItems:
            sub[1].stop()
        del self.SubscriptionDict[ServerSubHandle]

        # Unittest - fire deferred
        if self.UTEST:
                                
            msg = (time.time(),
                   'SubscriptionCancel',
                   None)
            self.UTEST_SUBMSGS[ServerSubHandle].append(msg)
            self.UTEST_MSGS.append(msg)
            # Fire deferred
            dkey = inOptions.get('ClientRequestHandle',None)
            UD = self.UTEST_DEFERSUB.pop(dkey,None)
            if UD:
                UD.callback(dkey)

        return IPH,inOptions,outOptions


    def Browse(self,(IPH,inOptions,outOptions)):
        ''' Create OPC Browse data
        '''

        # Browsing makes no sense without ItemName/ItemPath
        inOptions['ReturnItemName'] = True
        inOptions['ReturnItemPath'] = True

        # Check if there is IsItem, HasChildren
        PropertyNames = inOptions.get('PropertyNames',None)
        ReturnAllProperties = inOptions.get('ReturnAllProperties',None)

        if PropertyNames or ReturnAllProperties:
            # Retrieve properties for the items
            PIPH = ItemPairHolder()
            # Use outgoing Items for inItems of GetProperties()
            for inItem,outItem in IPH:
                PIPH.append(outItem,ItemContainer())
            d = defer.maybeDeferred(self.GetProperties,(PIPH,dict(
                PropertyNames = PropertyNames,
                ReturnAllProperties = ReturnAllProperties,
                ReturnPropertyValues = inOptions.get('ReturnPropertyValues',
                                                     None),
                ReturnItemPath=True,
                ReturnItemName=True,
                ReturnItemTime=True,
                ReturnErrorText=True),
                                                        {}))
            d.addCallback(self.FixOutValues)
            d.addCallback(self.__cbBrowse)
            return d
        else:
            # Immediately return result
            return IPH,inOptions,outOptions
        

    def __cbBrowse(self,(IPH,inOptions,outOptions)):
        ''' Process properties of the browse operation '''
        # Transfer various browse-specific attributes
        for inItem,outItem in IPH:
            outItem.Name = inItem.Name
            outItem.IsItem = inItem.IsItem
            outItem.HasChildren = inItem.HasChildren
        return IPH, inOptions, outOptions

    def GetProperties(self,(IPH,inOptions,outOptions)):
        ''' Create OPC GetProperties data
        '''
        # Pre-Read some variables
        ReturnPropertyValues = inOptions.get('ReturnPropertyValues',None)
        ReturnAllProperties = inOptions.get('ReturnAllProperties',None)
        PropertyNames = inOptions.get('PropertyNames',[])

        # These properties can be handled automatically
        specProperties = (QName(NS_XDA,'value',),
                          QName(NS_XDA,'quality'),
                          QName(NS_XDA,'timestamp'),
                          QName(NS_XDA,'scanRate'))
        ReadDict = {} # Dictionary needed for read method below
        for inItem,outItem in IPH:
            # Eventually Fill attributes: value/quality/timestamp
            for specProperty in specProperties:
                if getattr(self,'HandleProperty_'+specProperty.name, None) and \
                       not outItem.getProperty(specProperty.name) and \
                       (ReturnAllProperties or \
                        specProperty in PropertyNames):
                    if not ReadDict.has_key(mkItemKey(inItem)):
                        ReadDict[mkItemKey(inItem)] = (
                            inItem,  # needed for reading
                            outItem, # reference to the result
                            [])      # Denotes which values to fill 
                    if ReturnPropertyValues:
                        # Denote that a special property should be read
                        ReadDict[mkItemKey(inItem)][2].append(specProperty.name)
                    else:
                        # Add special (value-empty) property
                        outItem.addProperty(OPCProperty(Name=specProperty.name))

            for prop in outItem.listProperties():
                if not ReturnAllProperties:
                    # Delete property in case someone added a property which is not requested
                    if prop.Name not in PropertyNames:
                        outItem.delProperty(prop.Name)
                if not ReturnPropertyValues:
                    # Delete all values (in case someone accidentally
                    # added a value)
                    prop.Value = None
                if self.MkItemProperties and self.PropertyDelimiter:
                    # Set ItemPath/ItemName of Property
                    if prop.ItemName == None:
                        prop.ItemName = inItem.ItemName+\
                                        self.PropertyDelimiter+\
                                        prop.Name.name
                    if prop.ItemPath == None:
                        prop.ItemPath = inItem.ItemPath
            # Add Fault properties for requested properties that do not
            # exist in the outItem
            if not ReturnAllProperties:
                for reqProp in PropertyNames:
                    reqProp = QName(*reqProp)
                    if not outItem.getProperty(reqProp):
                        p=OPCProperty(Name=reqProp,
                                      ResultID=self.OPC_E_INVALIDPID,
                                      ErrorText='Requested Property "%s"'\
                                      'is unavailable' % str(reqProp))
                        outItem.addProperty(p)
                       

        # Read values if requested
        if ReturnPropertyValues and ReadDict:
            # First build ReadItemList
            RIPH = ItemPairHolder()
            for rin, rout, specs in ReadDict.itervalues():
                # Create an IPH for the read operation
                RIPH.append(rin,ItemContainer())

            if self.AutoItemCache:
                ReadOp=self.CachedRead
            else:
                ReadOp=self.Read
            d = defer.maybeDeferred(ReadOp,(RIPH,dict(ReturnItemName=True,
                                                      ReturnItemPath=True,
                                                      ReturnItemTime=True,
                                                      ReturnErrorText=True),
                                            {}))
            d.addCallback(self.FixOutValues)
            d.addCallback(self.__cbGetProperties,
                          IPH, inOptions, outOptions, ReadDict)
            return d
        else:
            # Immediately return result
            return IPH,inOptions,outOptions

    def __cbGetProperties(self,(RIPH,RinOptions,RoutOptions),
                         IPH, inOptions, outOptions, ReadDict):
        ''' Fill values from the read operation in the outItems '''
        for rin,rout in RIPH:
            # Build a dict of the values for easy retrieval
            ValDict = {'value' : rout.Value,
                       'quality' : rout.QualityField,
                       'timestamp' : rout.Timestamp,
                       # FIXME Calculate MaxSamplingRate on time(Read)
                       'scanRate' : self.MaxSamplingRate}

            # Get reference on the outItem and specs
            inItem,outItem,specs = ReadDict[mkItemKey(rin)]
            # Now add properties with values
            for spec in specs:
                # Set value for this spec, overwrite the whole property
                outItem.addProperty(OPCProperty(Name=spec,
                                                Value=ValDict[spec]))
                if self.MkItemProperties and self.PropertyDelimiter:
                    prop = outItem.getProperty(spec)
                    # Set ItemPath/ItemName of Property
                    prop.ItemName = inItem.ItemName+\
                                    self.PropertyDelimiter+\
                                    prop.Name.name
                    prop.ItemPath = inItem.ItemPath

        return IPH, inOptions, outOptions
        
    def render(self, request):
        ''' This customizes and the process method which is
        called anytime a request is received. '''

        # Set time the request was received
        self.rec_time = datetime.datetime.now()
        # Read incoming SOAP request
        soap_content = request.content.read()
        self.http_log('------------ Request -------------',
                      request.getAllHeaders(),
                      soap_content)


        # Retrieve SOAPAction and log the server access
        action = request.getHeader('SOAPAction')
        if action == None:
            action = ''
        else:
            # Remove beginning and trailing whitespace
            action = action.strip('" ')
        self.access_log('%s SOAPAction: %s' % (request.getClientIP(),
                                      action))

        # Set various header on outgoing HTTP response
        request.setHeader('Content-Type','text/xml')
        request.setHeader('Server','Twisted 2.1.0')

        s_action = action[action.rindex('/')+1:]
        operation = getattr(self,s_action,None)
        # Exception: Use CachedRead instead of Read if requested
        # through server attribute "AutoItemCache=True"
        if s_action == 'Read':
            if self.AutoItemCache:
                operation = getattr(self,'CachedRead',None)

        if operation:
            # Parse SOAP into typecode "tc_in" and
            # create response typcode "tc_out" 
            tc_in = getattr(OpcXmlDaSrv_services,s_action+'SoapIn', None)()
            tc_out = getattr(OpcXmlDaSrv_services,s_action+'SoapOut',
                                  None)()
        else:
            return self.SOAPFault(request,
                                  'client',
                                  'Errorenous or unimplemented SOAPAction: '
                                  '"%s"' % action)

        if not tc_in or not tc_out:
            return self.SOAPFault(request,
                                  'Client.RequestedOperation',
                                  'The requested operation is unknown')
        
        d = defer.maybeDeferred(self.parse_stage1,soap_content)
        # Now parse into typecode
        d.addCallback(self.parse_stage2,tc_in)
        # Fill ReplyBase
        d.addCallback(self.FillReplyBase)
        # Call actual operation
        d.addCallback(operation)
        # Fill/Fix various options and the IPH
        d.addCallback(self.FixOutValues)
        # Fill into typecode
        d.addCallback(self.serialize_stage1,tc_out)
        # Serialize and write out
        d.addCallback(self.serialize_stage2,request)

        # Add ErrorBack that handles various errors
        d.addErrback(self.handle_failure,request)

        # Indicate that the response is being processed asynchronously
        return server.NOT_DONE_YET


if __name__ == '__main__':

    # Start server
    root = resource.Resource()
    root.putChild('',XDAServer(http_log_fn='http.log'))
    site = server.Site(root)
    reactor.listenTCP(8000,site)
    reactor.run()
    
