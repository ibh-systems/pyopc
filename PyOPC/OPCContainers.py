#! /usr/bin/env python

'''OPC XMLDA 1.0 messages module
This module contains several messages for constructing requests/responses
for OPC operations such as Read/Write/Browse etc.'''

import decimal,time,datetime
import ZSI
import ZSI.fault

from utils import *

from OpcXmlDaSrv_services import *

class OPCBasic(object):
    ''' A class that defines basic functions for other OPC classes '''

    # All possible OPC Errors / Success codes
    # Success Codes
    OPC_S_CLAMP = (NS_XDA,'S_CLAMP')
    OPC_S_DATAQUEUEOVERFLOW = (NS_XDA,'S_DATAQUEUEOVERFLOW')
    OPC_S_UNSUPPORTEDRATE = (NS_XDA,'S_UNSUPPORTEDRATE')
    
    # Error Codes
    OPC_E_ACCESS_DENIED = QName(NS_XDA,'E_ACCESS_DENIED')
    OPC_E_BUSY = QName(NS_XDA,'E_BUSY')
    OPC_E_FAIL = QName(NS_XDA,'E_FAIL')
    OPC_E_INVALIDCONTINUATIONPOINT = QName(NS_XDA,'E_INVALIDCONTINUATIONPOINT')
    OPC_E_INVALIDFILTER = QName(NS_XDA,'E_INVALIDFILTER')
    OPC_E_INVALIDHOLDTIME = QName(NS_XDA,'E_INVALIDHOLDTIME')
    OPC_E_INVALIDITEMNAME = QName(NS_XDA,'E_INVALIDITEMNAME')
    OPC_E_INVALIDITEMPATH = QName(NS_XDA,'E_INVALIDITEMPATH')
    OPC_E_INVALIDPID = QName(NS_XDA,'E_INVALIDPID')
    OPC_E_NOSUBSCRIPTION = QName(NS_XDA,'E_NOSUBSCRIPTION')
    OPC_E_NOTSUPPORTED = QName(NS_XDA,'E_NOTSUPPORTED')
    OPC_E_OUTOFMEMORY = QName(NS_XDA,'E_OUTOFMEMORY')
    OPC_E_RANGE = QName(NS_XDA,'E_RANGE')
    OPC_E_BADTYPE = QName(NS_XDA,'E_BADTYPE')
    OPC_E_READONLY = QName(NS_XDA,'E_READONLY')
    OPC_E_SERVERSTATE = QName(NS_XDA,'E_SERVERSTATE')
    OPC_E_TIMEDOUT = QName(NS_XDA,'E_TIMEDOUT')
    OPC_E_UNKNOWNITEMNAME = QName(NS_XDA,'E_UNKNOWNITEMNAME')
    OPC_E_UNKNOWNITEMPATH = QName(NS_XDA,'E_UNKNOWNITEMPATH')
    OPC_E_WRITEONLY = QName(NS_XDA,'E_WRITEONLY')
    
    # PyOPC specific Error Codes
    PYO_E_EMPTYITEM = QName(NS_PYO,'E_EMTPYITEM')

    def setfrom_self_or_dict(self,Tdict,attrname,Tobj):
        ''' Set an attribute from a self attribute / dict entry
        with the same name / key unless the attribute == None '''
        v = getattr(Tobj,attrname,None)
        if v == None:
            t1 = getattr(self,attrname,None)
            t2 = Tdict.get(attrname,None)
            if t2 != None:
                setattr(Tobj,attrname,t2)
            elif t1 != None:
                setattr(Tobj,attrname,t1)

    def setfromattr(self, attr, outOptions):
        ''' Set dict item from self.attribute if not "None"'''
        value = getattr(self,attr,None)
        if value != None:
            outOptions[attr] = value

    def check_IClist(self,IClist):
        ''' Check if the given list contains only ItemContainers/None and
        expand possible sublists '''

        if isinstance(IClist,ItemContainer):
            # IClist is an ItemContainer itself, hence yield it
            if not IClist.IsEmpty:
                yield IClist
        elif isinstance(IClist,(list,tuple)):
            for item in IClist:
                for subitem in self.check_IClist(item):
                    yield subitem
        else:
            raise TypeError('Parameter is not of type ItemContainer: %s' %\
                            type(IClist))

    def fill_tcattrs(self,tc,attrs,Options):
        ''' Add element attributes to given typcode '''
        
        if getattr(tc,'_attrs',None) == None:
            tc._attrs={}

        for attr in attrs:
            # Either get them from the function parameters or
            # - if not available - from the object
            value = Options.pop(attr,getattr(self,attr,None))
            if value != None:
                # If value == None (NOT '', [], there's a difference!
                # the attribute is set
                # Some attributes have to be converted in some way
                # ReqType 
                if attr == 'ReqType':
                    tc._attrs[attr] = python2xsd(value)
                else:
                    tc._attrs[attr] = value


    def read_tcattrs(self,tc,attrs,d):
        ''' Read element attributes from typecode into given dictionary '''
        if getattr(tc,'_attrs',None):
            # Check if there is an attribute dictionary
            for attr in attrs:
                # Try to read attribute
                value = tc._attrs.get(attr,None)
                if value != None:
                    d[attr] = value

    def fill_tcelts(self,tc,elts,Options):
        ''' Fill element values from given Options '''
        for elt in elts:
            # Either get them from the function parameters or
            # - if not available - from the object
            value = Options.pop(elt,getattr(self,elt,None))
            if value != None:
                setattr(tc,elt,value)

    def read_tcelts(self,tc,elts,d):
        ''' Read element values from typecode into given dictionary '''
        for elt in elts:
            # Try to read element
            value = getattr(tc,elt,None)
            if value != None:
                d[elt] = value

class OPCOperation(OPCBasic):
    ''' Class that sets and reads OPC Operation typecodes '''

    # Address of the OPC server
    OPCServerAddress = ''

    # Element values and attributes of certain elements
    attrs_RequestOptions = ('ReturnErrorText',
                            'ReturnDiagnosticInfo',
                            'ReturnItemTime',
                            'ReturnItemPath',
                            'ReturnItemName',
                            'RequestDeadline',
                            'ClientRequestHandle',
                            'LocaleID')

    attrs_GetStatus = ('LocaleID',
                       'ClientRequestHandle')

    attrs_ReplyBase = ('RcvTime',
                       'ReplyTime',
                       'ClientRequestHandle',
                       'RevisedLocaleID',
                       'ServerState')

    attrs_ServerStatus = ('StartTime',
                          'ProductVersion')

    elts_ServerStatus = ('StatusInfo',
                         'VendorInfo',
                         'SupportedLocaleIDs',
                         'SupportedInterfaceVersions')

    attrs_ReadRequestItemList = ('ItemPath',
                                 'MaxAge',
                                 'ReqType')
    
    SubscribeRequestItemList = ('ItemPath',
                                'Deadband',
                                'RequestedSamplingRate',
                                'EnableBuffering',
                                'ReqType')

    attrs_SubscriptionPolledRefresh = ('HoldTime',
                                       'WaitTime',
                                       'ReturnAllItems')

    attrs_SubscriptionCancel = ('ServerSubHandle',
                                'ClientRequestHandle')

    attrs_Browse = ('LocaleID',
                    'ClientRequestHandle',
                    'ItemPath',
                    'ItemName',
                    'ContinuationPoint',
                    'MaxElementsReturned',
                    'BrowseFilter',
                    'ElementNameFilter',
                    'VendorFilter',
                    'ReturnAllProperties',
                    'ReturnPropertyValues',
                    'ReturnErrorText')

    attrs_BrowseResponse = ('ContinuationPoint',
                            'MoreElements')

    attrs_GetProperties = ('LocaleID',
                           'ClientRequestHandle',
                           'ItemPath',
                           'ReturnAllProperties',
                           'ReturnPropertyValues',
                           'ReturnErrorText')                       
    
    # Private variables
    _loc = None
    _portType = None

    def fill_tc(self, tc, IClist, Options):
        ''' Accepts a typecode and an Options Dictionary '''
        # FIXME
        # Workaround for ZSI
        # ZSI uses time, PyOPC instead uses datetime
        for key,value in Options.items():
            if isinstance(value,datetime.date):
                Options[key] = time.struct_time(value.utctimetuple())
        for i in self.check_IClist(IClist):
            if isinstance(i.Timestamp,datetime.date):
                i.Timestamp = time.struct_time(i.Timestamp.utctimetuple())
        
        # Extract the function string out of the typecode
        buf = extr_soap_type(tc)

        # If there is a self.ClientRequestHandle != None but no
        # ClientRequestHandle in Options, set and append a '_funcname' to it
        if Options.get('ClientRequestHandle', None) == None:
            v = getattr(self,'ClientRequestHandle',None)
            if v != None:
                Options['ClientRequestHandle'] = v + '_' + buf

        # Call the right function for this typecode
        func = getattr(self,'fill_'+buf,None)

        if func:
            # call proper function
            func(tc, IClist, Options)
        else:
            # ItemContainer does not provide a proper fill function for
            # this typecode
            raise AttributeError,'Unknown complex type %s for filling'%buf


    def read_tc(self, tc):
        ''' Accepts a typecode  '''

        # Call the right function for this typecode
        buf = extr_soap_type(tc)
        func = getattr(self,'read_'+buf,None)

        if func:
            # call proper function
            return func(tc)
        else:
            # ItemContainer does not provide a proper read function for
            # this typecode
            raise AttributeError,'Unknown complex type %s for reading'%buf

    ################# Private Fill / Read Methods for OPC Messages ############
    def __fill_RequestOptions(self, tc, IClist, Options):
        ''' Fill request options typecode '''
        # Fill attributes
        self.fill_tcattrs(tc, self.attrs_RequestOptions, Options)

    def __read_RequestOptions(self,tc):
        ''' Read RequestOptions '''
        Options = {}
        # Read Typecode attributes into dictionary
        self.read_tcattrs(tc, self.attrs_RequestOptions, Options)
        # FIXME ZSI-Limitation
        # Convert RequestDeadline
        RequestDeadline = Options.get('RequestDeadline',None)
        if RequestDeadline:
            if isinstance(RequestDeadline,float):
                RequestDeadline=time.localtime(RequestDeadline)
            Options['RequestDeadline']=datetime.datetime(*RequestDeadline[:6])
        # END ZSI-Limitation
        return Options

    def __fill_ReplyBase(self, tc, IClist, Options):
        ''' Fill ReplyBase Message '''
        # Set some attributes
        self.fill_tcattrs(tc, self.attrs_ReplyBase, Options)

    def __read_ReplyBase(self,tc):
        ''' Read ReplyBase '''
        Options = {}
        # Read Typecode attributes into dictionary
        self.read_tcattrs(tc, self.attrs_ReplyBase, Options)
        # FIXME ZSI-Limitation
        # Convert RcvTime and ReplyTime
        RcvTime = Options.get('RcvTime',None)
        if RcvTime:
            if isinstance(RcvTime,float):
                RcvTime=time.localtime(RcvTime)
            Options['RcvTime'] = datetime.datetime(*RcvTime[:6])
        ReplyTime = Options.get('ReplyTime',None)
        if ReplyTime:
            if isinstance(ReplyTime,float):
                ReplyTime=time.localtime(ReplyTime)
            Options['ReplyTime'] = datetime.datetime(*ReplyTime[:6])
        # END ZSI-Limitation
        
        return Options

    def __fill_OPCError(self,tc,error_dict):
        ''' Create and fill OPCError elements according to error_dict '''
        # Create error elements
        for key,value in error_dict.items():
            opcerr = tc.new_Errors()
            # set ResultID attribute and ErrorText
            opcerr.set_attribute_ID(key)
            opcerr.Text=value
            tc.Errors.append(opcerr)

    ################# Public Fill / Read Methods for OPC Messages ############
    ######################### GetStatus  #####################################
    def fill_GetStatus(self, tc, IClist, Options):
        ''' Fill GetStatus Operation '''
        # Set some attributes
        self.fill_tcattrs(tc, self.attrs_GetStatus, Options)

    def read_GetStatus(self,tc):
        ''' Read GetStatus Message '''
        rb = {}
        # Read Typecode attributes into dictionary
        self.read_tcattrs(tc, self.attrs_GetStatus, rb)
        return [], rb

    def fill_GetStatusResponse(self, tc, IClist, Options):
        ''' Fill getStatusResponse Message '''

        # Build ReplyBase
        tc.GetStatusResult = tc.new_GetStatusResult()
        # Now set the reply time
        self.__fill_ReplyBase(tc.GetStatusResult, IClist, Options)

        # Build Status element
        tc.Status = tc.new_Status()

        # Add attributes from the Status message
        self.fill_tcattrs(tc.Status, self.attrs_ServerStatus, Options)

        # Now add various elements
        self.fill_tcelts(tc.Status, self.elts_ServerStatus, Options)

    def read_GetStatusResponse(self, tc):
        ''' Read GetStatusResponse Message '''
        # The ReplyDictionary
        ReplyDict = {}
        # copy Reply base into ReplyDictionary
        ReplyDict.update(self.__read_ReplyBase(tc.GetStatusResult))

        # Add attributes from the Status message
        self.read_tcattrs(tc.Status, self.attrs_ServerStatus, ReplyDict)

        # FIXME ZSI-Limitation
        # Convert RequestDeadline
        StartTime = ReplyDict.get('StartTime',None)
        if StartTime:
            if isinstance(StartTime,float):
                StartTime=time.localtime(StartTime)
            ReplyDict['StartTime']=datetime.datetime(*StartTime[:6])
        # END ZSI-Limitation

        # Now add various elements
        self.read_tcelts(tc.Status, self.elts_ServerStatus, ReplyDict)
        
        return [], ReplyDict

   ######################### Read  #########################################
    def fill_Read(self, tc, IClist, Options):
        ''' Fill Read Message '''

        ReqHandleBase = Options.get('ClientRequestHandle',None)

        tc.Options = tc.new_Options()
        self.__fill_RequestOptions(tc.Options, [], Options)

        # Create and add the ItemList
        tc.ItemList = tc.new_ItemList()

        # Set ItemList attributes
        self.fill_tcattrs(tc.ItemList, self.attrs_ReadRequestItemList, Options)

        for i,item in enumerate(self.check_IClist(IClist)):
            item_tc = tc.ItemList.new_Items()

            # Override some ItemContainer attributes
            # Set a unique item handle if not specified
            if getattr(item,'ClientItemHandle',None) == None:
                if ReqHandleBase:
                    item.ClientItemHandle = ReqHandleBase+'Item_'+str(i)

            # Set attributes on typecode according to item
            item.fill_tc(item_tc)
            
            # Now append it to the item list
            tc.ItemList.Items.append(item_tc)

    def read_Read(self, tc):
        ''' Read Read Message '''

        ReplyDict = {}
        # Read RequestOptions
        ReplyDict.update(self.__read_RequestOptions(tc.Options))

        # Read ItemList attributes
        self.read_tcattrs(tc.ItemList,self.attrs_ReadRequestItemList,ReplyDict)

        ilist = []
        if tc.ItemList:
            for item in tc.ItemList.Items:
                ilist.append(ItemContainer(item,{}))

        return ilist, ReplyDict

    def fill_ReadResponse(self, tc, IClist, Options):
        ''' Fill ReadResponse Message '''

        # Build ReplyBase
        tc.ReadResult = tc.new_ReadResult()
        # Now set the reply base
        self.__fill_ReplyBase(tc.ReadResult, IClist, Options)

        tc.RItemList = tc.new_RItemList()

        # Now fill the request
        error_dict = {} # Error Dictionary
        for item in self.check_IClist(IClist):
            item_tc = tc.RItemList.new_Items()
            if item.ResultID:
                error_dict[item.ResultID]=item.ErrorText

            # Set attributes on typecode according to item
            item.fill_tc(item_tc)
            
            # Now append it to the item list
            tc.RItemList.Items.append(item_tc)

        self.__fill_OPCError(tc,error_dict)


    def read_ReadResponse(self, tc):
        ''' Read Read Response '''

        # The ReplyDictionary
        ReplyDict = {}
        # copy Reply base into ReplyDictionary
        ReplyDict.update(self.__read_ReplyBase(tc.ReadResult))
        
        # First build an error dictionary
        error_dict={}
        for error in tc.Errors:
            error_dict[error.get_attribute_ID()] = error.Text

        # Fill the item List
        ilist=[]

        if getattr(tc,'RItemList',None):
            for item in tc.RItemList.Items:
                ilist.append(ItemContainer(item,error_dict))
            
        return ilist, ReplyDict

    ############################ Write  #####################################
    def fill_Write(self, tc, IClist, Options):

        ''' Fill Write Operation '''
        ReqHandleBase = Options.get('ClientRequestHandle',None)

        # Make request options
        tc.Options = tc.new_Options()
        self.__fill_RequestOptions(tc.Options,[],Options)

        # Set required attribute ReturnValuesOnReply with default "False"
        # Set some attributes
        tc.set_attribute_ReturnValuesOnReply(\
            Options.pop('ReturnValuesOnReply',False))

        tc.ItemList = tc.new_ItemList()

        # Set attributes of ItemList
        self.fill_tcattrs(tc.ItemList, ['ItemPath'], Options)

        # Now fill the request
        for i,item in enumerate(self.check_IClist(IClist)):
            item_tc = tc.ItemList.new_Items()

            # Override some ItemContainer attributes
            # Set a unique item handle if not specified
            if getattr(item,'ClientItemHandle',None) == None:
                if ReqHandleBase:
                    item.ClientItemHandle = ReqHandleBase+'Item_'+str(i)

            # Set attributes on typecode according to item
            item.fill_tc(item_tc)
            
            # Now append it to the item list
            tc.ItemList.Items.append(item_tc)
        
    def read_Write(self, tc):
        ''' Read Write Message '''
        ReplyDict = {}
        # Read RequestOptions
        ReplyDict.update(self.__read_RequestOptions(tc.Options))
        # Read Write attributes
        self.read_tcattrs(tc, ['ReturnValuesOnReply'], ReplyDict)
        # Read ItemList attributes
        self.read_tcattrs(tc.ItemList, ['ItemPath'], ReplyDict)

        ilist = []
        if tc.ItemList:
            for item in tc.ItemList.Items:
                ilist.append(ItemContainer(item,{}))

        return ilist, ReplyDict

    def fill_WriteResponse(self, tc, IClist, Options):
        ''' Fill WriteResponse Message '''


        # Build ReplyBase
        tc.WriteResult = tc.new_WriteResult()
        # Now set the reply time
        self.__fill_ReplyBase(tc.WriteResult, IClist, Options)

        tc.RItemList = tc.new_RItemList()

        # Now fill the request
        error_dict = {} # Error Dictionary
        for item in self.check_IClist(IClist):
            item_tc = tc.RItemList.new_Items()
            if item.ResultID:
                error_dict[item.ResultID]=item.ErrorText

            # Set attributes on typecode according to item
            item.fill_tc(item_tc)
            
            # Now append it to the item list
            tc.RItemList.Items.append(item_tc)

        self.__fill_OPCError(tc,error_dict)


    def read_WriteResponse(self, tc):
        ''' Read Write Response '''
        # The ReplyDictionary
        ReplyDict = {}
        # copy Reply base into ReplyDictionary
        ReplyDict.update(self.__read_ReplyBase(tc.WriteResult))
        
        # First build an error dictionary
        error_dict={}
        for error in tc.Errors:
            error_dict[error.get_attribute_ID()] = error.Text

        # Fill the item List
        ilist=[]

        if getattr(tc.RItemList,'Items',None):
            for item in tc.RItemList.Items:
                ilist.append(ItemContainer(item,error_dict))
            
        return ilist,ReplyDict
            
    ######################### Subscribe  #####################################
    def fill_Subscribe(self, tc, IClist, Options):
        ''' Fill Subscribe Operation '''
        ReqHandleBase = Options.get('ClientRequestHandle',None)
        
        # Make request options
        tc.Options = tc.new_Options()
        self.__fill_RequestOptions(tc.Options,[],Options)

        # Set required attribute ReturnValuesOnReply with default "False"
        tc.set_attribute_ReturnValuesOnReply(\
            Options.pop('ReturnValuesOnReply',False))

        # Set SubscriptionPingRate
        self.fill_tcattrs(tc,['SubscriptionPingRate'],Options)

        tc.ItemList = tc.new_ItemList()

        # Fill Attributes
        self.fill_tcattrs(tc.ItemList, self.SubscribeRequestItemList,
                          Options)

        # Add Items
        for i,item in enumerate(self.check_IClist(IClist)):
            item_tc = tc.ItemList.new_Items()

            # Override some ItemContainer attributes
            # Set a unique item handle if not specified
            if getattr(item,'ClientItemHandle',None) == None:
                if ReqHandleBase:
                    item.ClientItemHandle = ReqHandleBase+'Item_'+str(i)

            # Set attributes on typecode according to item
            item.fill_tc(item_tc)
            
            # Now append it to the item list
            tc.ItemList.Items.append(item_tc)

    def read_Subscribe(self, tc):
        ''' Read Subscribe Message '''
        ReplyDict = {}
        # Read RequestOptions
        ReplyDict.update(self.__read_RequestOptions(tc.Options))
        # Read Write attributes
        self.read_tcattrs(tc, ('ReturnValuesOnReply',
                               'SubscriptionPingRate'),
                          ReplyDict)
        # Read ItemList attributes
        self.read_tcattrs(tc.ItemList, self.SubscribeRequestItemList,
                          ReplyDict)

        ilist = []
        for item in tc.ItemList.Items:
            ilist.append(ItemContainer(item,{}))

        return ilist, ReplyDict

    def fill_SubscribeResponse(self, tc, IClist, Options):
        ''' Fill SubscribeResponse Message '''
        # Build ReplyBase
        tc.SubscribeResult = tc.new_SubscribeResult()
        # Now set the reply time
        self.__fill_ReplyBase(tc.SubscribeResult, IClist, Options)

        self.fill_tcattrs(tc, ['ServerSubHandle'], Options)       
        tc.RItemList = tc.new_RItemList()
        self.fill_tcattrs(tc.RItemList, ['RevisedSamplingRate'], Options)

        # Now fill the request
        error_dict = {} # Error Dictionary
        for item in self.check_IClist(IClist):
            item_tc = tc.RItemList.new_Items()
            if item.ResultID:
                error_dict[item.ResultID]=item.ErrorText

            # Set attributes on typecode according to item
            item.fill_tc(item_tc)
            
            # Now append it to the item list
            tc.RItemList.Items.append(item_tc)

        self.__fill_OPCError(tc,error_dict)


    def read_SubscribeResponse(self, tc):
        ''' Read Subscribe Response '''
        # The ReplyDictionary
        ReplyDict = {}
        # copy Reply base into ReplyDictionary
        ReplyDict.update(self.__read_ReplyBase(tc.SubscribeResult))
        
        # Add Server SubHandle
        self.read_tcattrs(tc, ['ServerSubHandle'], ReplyDict)

        # First build an error dictionary
        error_dict={}
        for error in tc.Errors:
            error_dict[error.get_attribute_ID()] = error.Text

        ilist=[]
        # Also add attributes of RItemList = SubscribeReplyItemList
        # (which contains only RevisedSamplingRate)
        if getattr(tc,'RItemList',None):
            
            self.read_tcattrs(tc.RItemList, ['RevisedSamplingRate'],ReplyDict)

            # Fill the item List
            
            for item in tc.RItemList.Items:
                ilist.append(ItemContainer(item,error_dict))
            
        return ilist, ReplyDict


    ######################### SubscriptionPolledRefresh  ###################
    def fill_SubscriptionPolledRefresh(self, tc, IClist, Options):
        ''' Fill SubscriptionPolledRefresh Operation '''
        
        # Make request options
        tc.Options = tc.new_Options()
        self.__fill_RequestOptions(tc.Options,[],Options)

        # Set message attributes
        self.fill_tcattrs(tc,self.attrs_SubscriptionPolledRefresh,Options)
        
        # Add Server SubHandles
        if Options.has_key('ServerSubHandles'):
            pn = Options['ServerSubHandles']
            if isinstance(pn,basestring):
                pl = [pn]
            else:
                pl = list(pn)
            #try:
            #    # Workaround for ZSI: before .append, element has to be added
            #    tc.ServerSubHandles = pl[0]
            #except (IndexError):
            #    pass
            #for p in pl[1:]:
            #    tc.ServerSubHandles.append(p)
            tc.ServerSubHandles = pl
            del Options['ServerSubHandles']

    def read_SubscriptionPolledRefresh(self, tc):
        ''' Read SubscriptionPolledRefresh Message '''
        ReplyDict = {}
        # Read RequestOptions
        ReplyDict.update(self.__read_RequestOptions(tc.Options))
        # Read message attributes
        self.read_tcattrs(tc,self.attrs_SubscriptionPolledRefresh,ReplyDict)

        # FIXME ZSI-Limitation
        # Convert RequestDeadline
        HoldTime = ReplyDict.get('HoldTime',None)
        if HoldTime:
            if isinstance(HoldTime,float):
                HoldTime=time.localtime(HoldTime)
            ReplyDict['HoldTime']=datetime.datetime(*HoldTime[:6])
        # END ZSI-Limitation

        # Read ServerSubHandles
        if getattr(tc,'ServerSubHandles',None):
            hlist = []
            for item in tc.ServerSubHandles:
                hlist.append(item)
            # Append to ReplyDict if not empty
            if hlist:
                ReplyDict['ServerSubHandles'] = hlist
            
        return [], ReplyDict

    def fill_SubscriptionPolledRefreshResponse(self, tc, IClist, Options):
        ''' Fill SubscriptionPolledRefreshResponse Message '''
        # Build ReplyBase
        tc.SubscriptionPolledRefreshResult = tc.new_SubscriptionPolledRefreshResult()
        # Now set the reply time
        self.__fill_ReplyBase(tc.SubscriptionPolledRefreshResult,
                              IClist, Options)

        # Set message attributes
        self.fill_tcattrs(tc,['DataBufferOverflow'],Options)
        
        # Add Invalid Server SubHandles
        if Options.has_key('InvalidServerSubHandles'):
            pn = Options['InvalidServerSubHandles']
            if isinstance(pn,basestring):
                pl = [pn]
            else:
                pl = list(pn)
            #try:
            #    # Workaround for ZSI: before .append, element has to be added
            #    tc.InvalidServerSubHandles = pl[0]
            #except (IndexError):
            #    pass
            #for p in pl[1:]:
            #    tc.InvalidServerSubHandles.append(p)
            tc.InvalidServerSubHandles = pl
            del Options['InvalidServerSubHandles']
        
        # Here are two nested Item Lists due to possible different SubHandles
        # Therefore a dictionary is created with the SubHandle as key and
        # a list of ItemContainers as values
        item_dict = {}  # Item Dictionary with SubHandles as keys
        error_dict = {} # Error Dictionary
        for item in self.check_IClist(IClist):
            # Check if key exists, if not add key with empty list
            if not item_dict.get(item.SubscriptionHandle,None):
                item_dict[item.SubscriptionHandle] = []
            # Append item to list
            item_dict[item.SubscriptionHandle].append(item)

            # Fetch all errors
            if item.ResultID:
                error_dict[item.ResultID]=item.ErrorText
        
        for sh,ic in item_dict.items():
            ritem_tc=tc.new_RItemList()
            for item in ic:
                item_tc = ritem_tc.new_Items()
                # Set attributes on typecode according to item
                item.fill_tc(item_tc)
                # Now append it to a temporary list
                ritem_tc.Items.append(item_tc)
            tc.RItemList.append(ritem_tc)
            ritem_tc.set_attribute_SubscriptionHandle(sh)

        self.__fill_OPCError(tc,error_dict)


    def read_SubscriptionPolledRefreshResponse(self, tc):
        ''' Read SubscriptionPolledRefreshResponse '''
        # The ReplyDictionary
        ReplyDict = {}
        # copy Reply base into ReplyDictionary
        ReplyDict.update(self.__read_ReplyBase(tc.SubscriptionPolledRefreshResult))
        
        # Add DataBufferOverflow
        self.read_tcattrs(tc, ['DataBufferOverflow'], ReplyDict)

        # First build an error dictionary
        error_dict={}
        for error in tc.Errors:
            error_dict[error.get_attribute_ID()] = error.Text

        # Now get all invalid ServerSubHandles
        hl = []
        for handle in tc.InvalidServerSubHandles:
            hl.append(handle)
        if hl:
            # There are invalid handles, append to ReplyDict
            ReplyDict['InvalidServerSubHandles'] = hl

        # Fill the item List
        ilist=[]
        
        # Items are packed in RItemList as they have a distinct
        # attribute "SubscriptionHandle", therefore there have to
        # be two loops. However, there's only one item list,
        # the "SubscriptionHandle" is simply added to the ItemContainer
        for ritem in tc.RItemList:
            sh = ritem.get_attribute_SubscriptionHandle()
            for item in ritem.Items:
                ilist.append(ItemContainer(item,error_dict,
                                           SubscriptionHandle=sh))
            
        return ilist, ReplyDict

    ######################### SubscriptionCanel  #############################
    def fill_SubscriptionCancel(self, tc, IClist, Options):
        ''' Fill SubscriptionCancel Operation '''
        self.fill_tcattrs(tc,self.attrs_SubscriptionCancel,Options)

    def read_SubscriptionCancel(self, tc):
        ''' Read SubscriptionCancel Message '''
        ReplyDict = {}
        self.read_tcattrs(tc,self.attrs_SubscriptionCancel,ReplyDict)
        return [], ReplyDict

    def fill_SubscriptionCancelResponse(self, tc, IClist, Options):
        ''' Fill SubscriptionCancelResponse Message '''
        self.fill_tcattrs(tc,['ClientRequestHandle'],Options)


    def read_SubscriptionCancelResponse(self, tc):
        ''' Read SubscriptionCancelResponse '''

        # The ReplyDictionary
        ReplyDict = {}
        # copy Reply base into ReplyDictionary
        # There is no 'real' reply base, however there's only
        # ClientItemHandle, which is a member of ReplyBase, so it works
        ReplyDict.update(self.__read_ReplyBase(tc))

        return [], ReplyDict

    ######################### Browse  #####################################
    def fill_Browse(self, tc, IClist, Options):
        ''' Fill Browse Operation '''

        # Fill Browse message attributes
        self.fill_tcattrs(tc, self.attrs_Browse, Options)
        
        # Add PropertyNames
        if Options.has_key('PropertyNames'):
            pn = Options['PropertyNames']
            if isinstance(pn,basestring):
                pl = [pn]
            else:
                pl = list(pn)
            tc.PropertyNames = pl
            #try:
            #   # Workaround for ZSI: before .append, element has to be added
            #    tc.PropertyNames = pl[0]
            #except IndexError:
            #    pass
            #for p in pl[1:]:
            #    tc.PropertyNames.append(p)
            del Options['PropertyNames']

    def read_Browse(self, tc):
        ''' Read Browse Message '''
        ReplyDict = {}
        # Read Browse message attributes
        self.read_tcattrs(tc, self.attrs_Browse, ReplyDict)

        # Read PropertyNames
        pl = []
        for p in tc.PropertyNames:
            pl.append(p)
        if pl:
            ReplyDict['PropertyNames'] = pl
            
        return [], ReplyDict

    def fill_BrowseResponse(self, tc, IClist, Options):
        ''' Fill BrowseResponse Message '''
        # Build ReplyBase
        tc.BrowseResult = tc.new_BrowseResult()
        # Now set the reply time
        self.__fill_ReplyBase(tc.BrowseResult, IClist, Options)

        # Fill Browse message attributes
        self.fill_tcattrs(tc, self.attrs_BrowseResponse, Options)

        # Fill in the Browse Elements
        error_dict = {} # Error Dictionary
        for item in self.check_IClist(IClist):
            if item.ResultID:
                error_dict[item.ResultID]=item.ErrorText
            item_tc = tc.new_Elements()
            # Set error dictionary from properties
            for prop in item.listProperties():
                if prop.ResultID:
                    error_dict[prop.ResultID] = prop.ErrorText

            # Set attributes on typecode according to item
            item.fill_tc(item_tc)
            
            # Now append it to the item list
            tc.Elements.append(item_tc)

        self.__fill_OPCError(tc,error_dict)
        

    def read_BrowseResponse(self, tc):
        ''' Read Browse Response '''
        # The ReplyDictionary
        ReplyDict = {}
        # copy Reply base into ReplyDictionary
        ReplyDict.update(self.__read_ReplyBase(tc.BrowseResult))

        self.read_tcattrs(tc, self.attrs_BrowseResponse, ReplyDict)
        
        
        # First build an error dictionary
        error_dict={}
        for error in tc.Errors:
            error_dict[error.get_attribute_ID()] = error.Text

        # Fill the item List
        ellist=[]

        for element in tc.Elements:
            ellist.append(ItemContainer(element,error_dict))
            
        return ellist,ReplyDict

    ######################### GetProperties ##################################
    def fill_GetProperties(self, tc, IClist, Options):
        ''' Fill GetProperties Operation '''
        # Add all other options to the GetProperties Request
        self.fill_tcattrs(tc, self.attrs_GetProperties, Options)

        # Add Item IDs
        for item in self.check_IClist(IClist):
            item_id = tc.new_ItemIDs()

            # Set attributes on typecode according to item
            item.fill_tc(item_id)
            
            # Now append it to the item list
            tc.ItemIDs.append(item_id)

        # Add PropertyNames
        if Options.has_key('PropertyNames'):
            pl = list(Options['PropertyNames'])
            tc.PropertyNames = pl
            #try:
            #    # Workaround for ZSI: before .append, element has to be added
            #    tc.PropertyNames = pl[0]
            #except IndexError:
            #    pass
            #for p in pl[1:]:
            #    tc.PropertyNames.append(p)
            del Options['PropertyNames']

    def read_GetProperties(self, tc):
        ''' Read Read Message '''
        ReplyDict = {}
        # Read GetProperties message attributes
        self.read_tcattrs(tc, self.attrs_GetProperties, ReplyDict)

        # Read Item IDs
        ilist = []
        for item in tc.ItemIDs:
            ilist.append(ItemContainer(item,{}))

        # Read PropertyNames
        pl = []
        for p in tc.PropertyNames:
            pl.append(p)
        if pl:
            ReplyDict['PropertyNames'] = pl
            
        return ilist, ReplyDict

    def fill_GetPropertiesResponse(self, tc, IClist, Options):
        ''' Fill GetPropertiesResponse Message '''
        # Build ReplyBase
        tc.GetPropertiesResult = tc.new_GetPropertiesResult()
        # Now set the reply time
        self.__fill_ReplyBase(tc.GetPropertiesResult, IClist, Options)

        # Fill in the PropertyLists
        error_dict = {} # Error Dictionary
        for item in self.check_IClist(IClist):
            if item.ResultID:
                error_dict[item.ResultID]=item.ErrorText
            item_tc = tc.new_PropertyLists()
            # Set error dictionary from properties
            for prop in item.listProperties():
                if prop.ResultID != None:
                    error_dict[prop.ResultID] = prop.ErrorText
                    
            # Set attributes on typecode according to item
            item.fill_tc(item_tc)
            
            # Now append it to the item list
            tc.PropertyLists.append(item_tc)

        self.__fill_OPCError(tc,error_dict)
        

    def read_GetPropertiesResponse(self, tc):
        ''' Read GetPropertiesResponse Response '''

        # The ReplyDictionary
        ReplyDict = {}
        # copy Reply base into ReplyDictionary
        ReplyDict.update(self.__read_ReplyBase(tc.GetPropertiesResult))
        
        # First build an error dictionary
        error_dict={}
        for error in tc.Errors:
            error_dict[error.get_attribute_ID()] = error.Text

        # Fill the item List
        ellist=[]

        for element in tc.PropertyLists:
            ellist.append(ItemContainer(element,error_dict))
            
        return ellist,ReplyDict

    
class ItemContainer(OPCBasic,NoNewAttrs):
    ''' Class that may be used for various requests/responses
    Basically it holds an item specifier (ItemPath/ItemName) and
    additional properties, such as Value, Quality etc. '''

    ########## Server specific attributes ###########
    # An Item that "IsEmpty" will be handled like "None" by various
    # Functions. This is a better way than to use "None" as such
    # objects can be passed by reference
    # The default is "False", e.g. the ItemContainer is NOT empty.
    IsEmpty = True
    # Special Sequence Number that is used for splitting/joining Items
    Sequence=None
    CacheTimestamp=None
    # Indicates if an Item was Read by SubscriptionPolledRefresh
    IsRead = None

    ######### Attributes that have a corresponding SOAP part ########
    ItemName=None
    ItemPath=None

    Value=None
    Timestamp=None
    ValueTypeQualifier=None
    MaxAge=None
    ReqType=None
    # FIXME This has to be implemented
    ReadDelay=None
    WriteDelay=None

    ClientItemHandle=None

    ResultID=None
    DiagnosticInfo=None
    ErrorText=None

    # Quality 
    QualityField=None
    LimitField=None
    VendorField=None
    
    # For Subscription
    Deadband = None
    RequestedSamplingRate = None
    EnableBuffering = None
    RevisedSamplingRate = None
    SubscriptionHandle = None

    # For Browse Responses
    Name = None
    IsItem = None
    HasChildren = None

    # Holds properties
    _Properties = None

    attrs_ReadRequestItem = ('ItemPath',
                             'ReqType',
                             'ItemName',
                             'ClientItemHandle',
                             'MaxAge')

    attrs_SubscribeRequestItem = ('ItemPath',
                                  'ItemName',
                                  'ReqType',
                                  'ClientItemHandle',
                                  'Deadband',
                                  'RequestedSamplingRate',
                                  'EnableBuffering',
                                  'ItemPath')
    
    attrs_BrowseElement = ('Name',
                           'ItemPath',
                           'ItemName',
                           'IsItem',
                           'HasChildren')
    
    attrs_ItemIdentifier = ('ItemName',
                            'ItemPath')

    attrs_ItemValue = ('ValueTypeQualifier',
                       'ItemPath',
                       'ItemName',
                       'ClientItemHandle',
                       'Timestamp',
                       'ResultID')


    attrs_OPCQuality = ('QualityField',
                        'LimitField',
                        'VendorField')
    
    def __repr__(self):
        l = []
        for key,value in self.__dict__.items():
            l.append('%s=%s' % (key,value))
        return '%s(%s)' % (self.__class__.__name__,', '.join(l))

    def __init__(self,tc=None,error_dict=None,**kwds):
        ''' Set object attributes from given typecode or from keywords '''

        # Create/Shadow mutable default values
        self._Properties = {}
        super(ItemContainer,self).__setattr__("IsEmpty",True)

        if tc:
            # Call the right function for this typecode
            buf = extr_soap_type(tc)
            func = getattr(self,'read_'+buf,None)

            if func:
                # call proper function
                func(tc,error_dict)
            else:
                # ItemContainer does not provide a proper read function for
                # this typecode
                raise AttributeError,'Unknown complex type %s for reading'%buf


        # Now set attributes accordings to keywords
        # (Maybe overriding values given in the typecode)
        for key,value in kwds.items():
            setattr(self,key,value)


    def __setattr__(self,name,value):
        ''' If any attribute is set, it is "Not Empty" any more '''
        if name != "IsEmpty":
            # Set IsEmpty to False
            super(ItemContainer,self).__setattr__("IsEmpty",False)
        # Call the superclasses method
        super(ItemContainer,self).__setattr__(name,value)

    def __cmp__(self,other):
        ''' Compare Item Values - For sorting after SubHandle, ItemPath/Name'''
        if self.SubscriptionHandle < other.SubscriptionHandle:
            return -1
        if self.SubscriptionHandle > other.SubscriptionHandle:
            return 1
        if self.ItemPath < other.ItemPath:
            return -1
        if self.ItemPath > other.ItemPath:
            return 1
        if self.ItemName < other.ItemName:
            return -1
        if self.ItemName > other.ItemName:
            return 1
        return 0

    def addProperty(self,prp):
        ''' Add/Update property of this item '''
        # Denote that the item has been accessed
        self.IsEmpty = False
        if prp.Name == None:
            raise ValueError('Property has no name!')
        self._Properties[prp.Name] = prp

    def addProperties(self,prps):
        ''' Add/Update multiple properties of this item '''
        if prps:
            for prp in prps:
                self.addProperty(prp)

    def getProperty(self,name):
        ''' Get Property from item '''
        if isinstance(name,basestring):
            # Build a QName from a string
            if OPCProperties.has_key(name):
                # Maybe the property is an OPC property?
                name = QName(NS_XDA,name)
            else:
                # Use the PyOPC namespace
                name = QName(NS_PYO,name)
        return self._Properties.get(name,None)

    def popProperty(self,name):
        ''' Pop Property from item '''
        return self._Properties.pop(name,None)

    def delProperty(self,name):
        ''' Delete Property from item '''
        del self._Properties[name]

    def listProperties(self):
        ''' Return all properties in a list '''
        return self._Properties.values()

    def mapProperties(self):
        ''' Return a dictionary of all properties, with name as key '''
        return self._Properties
    
    def fill_tcattrs(self,tc,attrs):
        ''' Add attributes to given typecode (altered, no Options here)'''
        OPCBasic.fill_tcattrs(self,tc,attrs,{})


    def read_tcattrs(self,tc,attrs):
        ''' Add given attributes to instance '''
        if getattr(tc,'_attrs',None):
            for attr in attrs:
                value = tc._attrs.get(attr,None)
                if value != None:
                    setattr(self,attr,value)

    def fill_tcelts(self,tc,elts):
        ''' Set elements to given typecode (altered, no Options here) '''
        OPCBasic.fill_tcelts(self,tc,elts,{})

    def read_tcelts(self,tc,elts):
        ''' Set instance attrs from given typecode '''
        for elt in elts:
            value = getattr(tc,elt,None)
            if value != None:
                setattr(self,elt,value)


    def fill_tcValue(self,tc,value=None):
        ''' Add Value element to Typecode '''
        if value == None:
            value = self.Value
        if value != None:
            # Value can be of various types, try to find out of which one
            if isinstance(value,(list,tuple)) and \
                   not isinstance(value, QNameValue):
                # FIXME Lists in Lists are not supported by now
                # Get appropriate Array Type
                ArrayXSD = python2xsd(value)[1] # Like "ArrayOfInt"
                ArrayType = globals()[ArrayXSD] # The corr. object
                ValueAttr = ArrayXSD[7:]        # Like "Int"
                tc.Value = ArrayType()          # Add to Typecode
                tmpval = list(value)            # Copy original
                setattr(tc.Value,ValueAttr,tmpval)
                ## Set the first value
                #setattr(tc.Value,ValueAttr,tmpval.pop(0))
                ## Get back the reference to the list
                #ValueList = getattr(tc.Value,ValueAttr)
                #for i in tmpval:
                #    ValueList.append(i)
            elif isinstance(value,(datetime.date,
                                   datetime.time)):
                # Datetime-Based
                # FIXME should be altered when ZSI is datetime-capable
                tc.Value=time.struct_time(value.utctimetuple())
                # FIXME add ValueTypeQualifer to typecode
            elif isinstance(value,(basestring,
                                   bool,
                                   float,
                                   # FIXME decimal,
                                   int,
                                   long,
                                   QNameValue)):
                tc.Value=value
            else:
                # Unknown data type, hence raise an error
                raise TypeError('Datatype %s cannot be serialized' % value)

    def read_tcValue(self,tc):
        ''' Read Value element from Typecode '''
        value = tc.Value

        if isinstance(value,tuple) and len(value) == 2:
            try:
                value = QNameValue(value[0],value[1])
            except TypeError:
                # This seems to be no QName, hence leave value "as-is"
                pass

        # FIXME ZSI-Limitation
        # Convert time-based value into datetime
        if isinstance(value,tuple) and len(value) == 9:
            # Convert to a struct_time
            value = time.struct_time(value)
        if isinstance(value,time.struct_time):
            # FIXME Honor ValueTypeQualifer - could also be time/date
            value = datetime.datetime(*value[:6])
        # END ZSI-Limitation
        if hasattr(value,'typecode'):
            # This could be an Array
            t = value.typecode.type
            if t[0] == NS_XDA and 'ArrayOf' in t[1]:
                # Now get the element name
                # This is silly, but what else could I do?                
                ElementName = '_'+t[1][7].lower()+t[1][8:]
                value =  getattr(value,ElementName)
            
        if value != None:
            self.Value = value

    def fill_tc(self,tc):
        ''' Fill given typecode with values in this class '''

        # Call the right function for this typecode

        buf = extr_soap_type(tc)
        func = getattr(self,'fill_'+buf,None)

        if func:
            # call proper function
            func(tc)
        else:
            # ItemContainer does not provide a proper fill function for
            # this typecode
            raise AttributeError,'Complex type %s can not be filled' % buf
        

    def fill_ReadRequestItem(self,tc):
        ''' Fill given ReadRequestItem with appropriate Values '''
        self.fill_tcattrs(tc, self.attrs_ReadRequestItem)
        

    def read_ReadRequestItem(self,tc,error_dict):
        ''' Read contents of ReadRequestItem '''
        self.read_tcattrs(tc, self.attrs_ReadRequestItem)


    def fill_SubscribeRequestItem(self,tc):
        ''' Fill SubscribeRequestItem typecode from object '''
        self.fill_tcattrs(tc, self.attrs_SubscribeRequestItem)

    def read_SubscribeRequestItem(self,tc,error_dict):
        ''' Read SubscribeRequestItem typecode into object '''
        self.read_tcattrs(tc, self.attrs_SubscribeRequestItem)

    def fill_BrowseElement(self,tc):
        ''' Fill BrowseResponse typecode from object '''
        self.fill_tcattrs(tc, self.attrs_BrowseElement)

        # Fill Properties
        for prop in self.listProperties():
            p = tc.new_Properties()
            if prop.Value != None:
                self.fill_tcValue(p,prop.Value)
            if prop.Name != None:
                p.set_attribute_Name(prop.Name)
            if prop.Description != None:
                p.set_attribute_Description(prop.Description)
            if prop.ItemPath != None:
                p.set_attribute_ItemPath(prop.ItemPath)
            if prop.ItemName != None:
                p.set_attribute_ItemName(prop.ItemName)
            if prop.ResultID != None:
                p.set_attribute_ResultID(prop.ResultID)

            tc.Properties.append(p)

        
    def read_BrowseElement(self,tc,error_dict):
        ''' Read BrowseResponse typecode into object '''
        self.read_tcattrs(tc, self.attrs_BrowseElement)
        
        for prp in tc.Properties:
            # Retrieve first as it's needed below for ErrorText
            ResultID = prp.get_attribute_ResultID()
            if ResultID:
                ResultID = QName(*ResultID)

            p = OPCProperty(\
                Name = QName(*prp.get_attribute_Name()),
                Description = prp.get_attribute_Description(),
                ItemPath = prp.get_attribute_ItemPath(),
                ItemName = prp.get_attribute_ItemName(),
                ResultID = ResultID,
                ErrorText = error_dict.get(ResultID,None))

            if prp.Value:
                p.Value = prp.Value

            self.addProperty(p)


    def fill_ItemIdentifier(self,tc):
        ''' Fill ItemIdentifier typecode from object '''
        self.fill_tcattrs(tc, self.attrs_ItemIdentifier)

    def read_ItemIdentifier(self,tc,error_dict):
        ''' Read ItemIdentifier typecode into object '''
        self.read_tcattrs(tc, self.attrs_ItemIdentifier)


    def fill_PropertyReplyList(self,tc):
        ''' Fill PropertyReplyList typecode from object '''

        self.fill_tcattrs(tc, ('ItemPath','ItemName','ResultID'))

        # Fill Properties
        for prop in self.listProperties():
            p = tc.new_Properties()
            if prop.Value != None:
                self.fill_tcValue(p,prop.Value)
            if prop.Name != None:
                p.set_attribute_Name(prop.Name)
            if prop.Description != None:
                p.set_attribute_Description(prop.Description)
            if prop.ItemPath != None:
                p.set_attribute_ItemPath(prop.ItemPath)
            if prop.ItemName != None:
                p.set_attribute_ItemName(prop.ItemName)
            if prop.ResultID != None:
                p.set_attribute_ResultID(prop.ResultID)

            tc.Properties.append(p)


    def read_PropertyReplyList(self,tc,error_dict):
        ''' Read PropertyReplyList typecode into object '''

        self.read_tcattrs(tc, ('ItemPath','ItemName','ResultID'))
            
        ResultID = tc.get_attribute_ResultID()
        if ResultID:
            ResultID = QName(*ResultID)
            # There is an error
            self.ResultID=ResultID
            self.ErrorText = error_dict.get(ResultID,None)

        for prp in tc.Properties:
            # Retrieve first as it's needed below for ErrorText
            PResultID = prp.get_attribute_ResultID()
            if PResultID:
                PResultID = QName(*PResultID)

            p = OPCProperty(\
                Name = QName(*prp.get_attribute_Name()),
                Description = prp.get_attribute_Description(),
                ItemPath = prp.get_attribute_ItemPath(),
                ItemName = prp.get_attribute_ItemName(),
                ResultID = PResultID,
                ErrorText = error_dict.get(PResultID,None))

            if prp.Value:
                p.Value = prp.Value

            self.addProperty(p)


    ################### Item Value based ##################

    def fill_ItemValue(self,tc):
        ''' Fill ItemValue typecode from object '''

        # First set all attributes of ItemValue element
        self.fill_tcattrs(tc, self.attrs_ItemValue)
        
        # Now add and set elements
        self.fill_tcelts(tc,['DiagnosticInfo'])
        # Now fill the Value
        self.fill_tcValue(tc)
        
        tc.Quality = tc.new_Quality()
        self.fill_tcattrs(tc.Quality, self.attrs_OPCQuality)
        

    def read_ItemValue(self,tc,error_dict):
        ''' Read ItemValue typecode into object '''

        self.read_tcattrs(tc, self.attrs_ItemValue)

        # FIXME ZSI-Limitation
        # Convert RequestDeadline
        if self.Timestamp:
            if isinstance(self.Timestamp,float):
                self.Timestamp=time.localtime(self.Timestamp)
            self.Timestamp=datetime.datetime(*self.Timestamp[:6])
        # END ZSI-Limitation

        self.read_tcelts(tc,['DiagnosticInfo'])
        # Now read the Value
        self.read_tcValue(tc)
        
        if getattr(tc,'Quality',None):
            self.read_tcattrs(tc.Quality, self.attrs_OPCQuality)
         
        if self.ResultID:
            # There is an error
            self.ErrorText = error_dict.get(self.ResultID,None)


    def fill_SubscribeItemValue(self,tc):
        ''' Function that handles attribute and calls fill_ItemValue '''

        tc.ItemValue = tc.new_ItemValue()
        self.fill_tcattrs(tc,['RevisedSamplingRate'])
        self.fill_ItemValue(tc.ItemValue)

    def read_SubscribeItemValue(self,tc,error_dict):
        ''' Function that handles attribute and calls read_ItemValue '''

        self.read_ItemValue(tc.ItemValue,error_dict)
        self.RevisedSamplingRate=tc.get_attribute_RevisedSamplingRate()

    def fill_SubscribePolledRefreshReplyItemList(self,tc):
        ''' Function that handles attribute and calls fill_ItemValue '''

        self.fill_ItemValue(tc)

    def read_SubscribePolledRefreshReplyItemList(self,tc,error_dict):
        ''' Function that handles attribute and calls read_ItemValue '''

        self.read_ItemValue(tc,error_dict)


if __name__ == '__main__':
    # Test some functions

    pass


    
