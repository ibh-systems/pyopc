#!/usr/bin/env python
import unittest, sys, time, decimal, datetime, xml, copy
from PyOPC.OPCContainers import *
from PyOPC import OpcXmlDaSrv_services


def expanddict(d):
    ''' Yield all values + keys in a dict and expand lists/tuples '''
    # Fist delete unwanted values
    # Make a copy first
    d = dict(d)
    d.pop('IsEmpty',None)
    d.pop('_Properties',None)
    
    for i in d.keys()+d.values():
        if isinstance(i,(list,tuple)):
            for x in i:
                yield x
        elif isinstance(i,dict):
            if isinstance(i.values()[0],OPCProperty):
                for props in i.values():
                    for j in props:
                        yield j
        elif isinstance(i,QName):
            for j in tuple(i):
                yield j
        else:
            yield i

def tosoapstr(item):
    ''' Convert arbitrary value to SOAP string '''
    if isinstance(item,float) \
           and item > 1000000000 \
           and item < 2000000000:
        # This seems to be a date, hence convert it
        # microseconds are currently not supported by ZSI
        #d=datetime.datetime.fromtimestamp(item)
        d=datetime.datetime.utcfromtimestamp(int(item))
        # Convert it to ISO Format
        item = d.isoformat()
        
    if isinstance(item,bool):
        item = str(item).lower()
    if isinstance(item,tuple) and len(item) == 2:
        # This seems to be a QName tuple, search only for the second part
        item = item[1]
    if isinstance(item,datetime.datetime):
        item = item.isoformat()
    
    return str(item)


def cmp_dict_list(d1,d2, cmpsorted=False):
    ''' Compare dictionaries while optionally ignoring order of list values '''
    # Make a copy
    d1=dict(d1)
    d2=dict(d2)

    for k1 in d1.keys():
        v1 = d1.pop(k1)
        try:
            # Try to retrieve value of key1 from dict2
            v2 = d2.pop(k1)
            
        except KeyError:
            return 'Key %s is missing in *received* dictionary\n'\
                   '%s\n%s\n'% (k1,d1.keys(),d2.keys())


        if isinstance(v1,dict) and v1 != {} and \
               isinstance(v1.values()[0],OPCProperty):
            # This is a PropertyContainer
            td1 = {}
            td2 = {}
            for key,value in v1.items():
                td1[key] = list(value)
            for key,value in v2.items():
                td2[key] = list(value)
            v1=td1
            v2=td2

            
        # Ignore order of lists/tuples
        if cmpsorted and isinstance(v1,(list,tuple)):
            # Copy - it may be a tuple
            v1 = list(v1)
            v1.sort()
            v2 = list(v2)
            v2.sort()
            if v1 != v2:
                return 'Dict items differ on key "%s":\n'\
                       '*sent* value:\n%s\n*sent* type:%s\n'\
                       '*received value:\n%s\n*received* type:%s\n' %\
                       (k1,v1,type(v1),v2,type(v2))
            
        else:
            if v1 != v2:
                return 'Dict items differ on key "%s":\n'\
                       '*sent* value:\n%s\n*sent* type:%s\n'\
                       '*received value:\n%s\n*received* type:%s\n' %\
                       (k1,v1,type(v1),v2,type(v2))

    if len(d1) != 0 or len(d2) != 0:
        return 'Given Dict1 != Received Dict2:\n%s\n!=\n%s' % (d1,d2)
    else:
        return ''


class QNameValueCheck(unittest.TestCase):
    ''' Test QNameValue typecode '''

    def testInit(self):
        ''' Initialize a QNameValue '''
        q = QNameValue('urn:abc','blabla')
        # Test the repr function
        q1 = eval(repr(q))
        q2 = QNameValue('urn:abc','quaquq')
        # convert to a tuple
        self.assertEqual(tuple(q),('urn:abc','blabla'))
        # str should also work
        self.assertEqual(str(q),"QNameValue('urn:abc', 'blabla')")
        # Comparisons should also work
        self.assertEqual(q==q1,True)
        self.assertEqual(q!=q1,False)
        self.assertEqual(q==q2,False)
        self.assertEqual(q!=q2,True)
        # The typcode should also fit
        self.failUnless(isinstance(q.typecode,ZSI.TC.QName))
        # Only valid scheme/value pairs should be accepted
        self.assertRaises(TypeError,QNameValue,'urn:abc',234)
        self.assertRaises(ValueError,QNameValue,'urnabc','abc')

class xsd2pythonCheck(unittest.TestCase):
    ''' Test for xsd2python '''

    trans=(('','string','String'),
           (1,'int','Int'),
           (1234213421341234214123,'long','Long'),
           (True,'boolean','Boolean'),
           (1.42,'double','Double'),
           (decimal.Decimal('12.2'),'decimal','Decimal'),
           (datetime.datetime.now(),'dateTime','DateTime'),
           (QNameValue,'QName',None),
           (datetime.time(12,20),'time',None),
           (datetime.date(12,2,25),'date',None),
           (datetime.timedelta(10),'duration',None))
    
    def testDirect(self):
        ''' xsd2python should accept python equivalent types '''
        for t in self.trans:
            self.assertEqual(python2xsd(t[0]), (NS_XSD,t[1]))

    def testType(self):
        ''' xsd2python should accept python equivalent type(types) '''
        for t in self.trans:
            if t[0] != QNameValue:
                self.assertEqual(python2xsd(type(t[0])), (NS_XSD,t[1]))

    def testListDirect(self):
        ''' xsd2python should accept lists of python types '''
        for t in self.trans:
            if t[2] == None:
                self.assertRaises(XSDTypeError, python2xsd, [t[0]])
            else:
                self.assertEqual(python2xsd([t[0]]), (NS_XDA,'ArrayOf'+t[2]))

    def testList(self):
        ''' test various lists '''
        self.assertEqual(python2xsd([1,2,3]),(NS_XDA,'ArrayOfInt'))
        self.assertEqual(python2xsd([1.0,2.2,3.3]),(NS_XDA,'ArrayOfDouble'))
        self.assertEqual(python2xsd([[1],2,3]),(NS_XDA,'ArrayOfAnyType'))
        self.assertEqual(python2xsd([1,2.2]),(NS_XDA,'ArrayOfAnyType'))
        self.assertEqual(python2xsd([1,'a']),(NS_XDA,'ArrayOfAnyType'))
        

    def testErrors(self):
        ''' xsd2python should raise XSDTypeError for wrong unknown types '''
        self.assertRaises(XSDTypeError, python2xsd, [])
        self.assertRaises(XSDTypeError, python2xsd, set([1, 2, 3]))
        self.assertRaises(XSDTypeError, python2xsd, [set([1, 2, 3])])
        self.assertRaises(XSDTypeError, python2xsd, type(set([1, 2, 3])))
        self.assertRaises(XSDTypeError, python2xsd, None)
        self.assertRaises(XSDTypeError, python2xsd, [datetime.time(12,12,12)])
        self.assertRaises(XSDTypeError, python2xsd, [])
        self.assertRaises(XSDTypeError, python2xsd, ())
        self.assertRaises(XSDTypeError, python2xsd, [1,2,set([1,2,3])])
        self.assertRaises(XSDTypeError, python2xsd, [1,2,datetime.time(12,12)])


class ItemContainerCheck(unittest.TestCase):
    ''' Test OPCItemContainer '''

    def testcheck_ICList(self):
        ''' Test the simple check_ICList function which expands lists'''
        b = OPCBasic()
        # Testcase of successful examples
        t=[ItemContainer(IsEmpty=False),
           [ItemContainer(IsEmpty=False),
            ItemContainer(IsEmpty=False),
            ItemContainer(IsEmpty=False)],
           [ItemContainer(IsEmpty=False),
            [ItemContainer(IsEmpty=False),
             ItemContainer(IsEmpty=False)],
            ItemContainer(IsEmpty=False)],
           (ItemContainer(IsEmpty=False),
            ItemContainer(IsEmpty=False),
            (ItemContainer(IsEmpty=False),
             ItemContainer(IsEmpty=False)))]
        # Result of len()
        tres=[1,3,4,4]
        for i,j in enumerate(t):
            c=0
            for item in b.check_IClist(j):
                self.failUnless(isinstance(item,ItemContainer))
                c+=1
            self.assertEqual(c,tres[i])

        def dummyfail(ic):
            for i in b.check_IClist([ItemContainer(IsEmpty=False),'abc']):
                pass


        # this should raise a TypeError
        self.assertRaises(TypeError, dummyfail)


class OPCPropertyCheck(unittest.TestCase):
    ''' Test OPCPropertyContainer '''

    testcases_ok = ((QName('urn:bla','value'),
                     1,'Item Value', '', 'Lightswitch1', None, None),
                    (QName('urn:qua','accessRights'),
                     'rw','AccessRights', 'bla', 'qua', None, None))
                 
    
    def testTupleAssign(self):
        ''' Assign tuples to PropertyContainer '''
        for t in self.testcases_ok:
            p = OPCProperty(*t)
            self.assertEqual(tuple(p),t)
            self.assertEqual(p.Value,t[1])

    def testDictAssign(self):
        ''' Create Property via Keyword '''
        p = OPCProperty(Name=QName('urn:bla','value'),
                        Value=1,
                        Description='Item Value',
                        ItemPath='',
                        ItemName='Lightswitch1')
        self.assertEqual(tuple(p),self.testcases_ok[0])

    def testAttributes(self):
        p = OPCProperty()
        p.Name=QName('urn:bla','value')
        p.Value=1
        p.Description='Item Value'
        p.ItemPath=''
        p.ItemName='Lightswitch1'
            
        self.assertEqual(tuple(p),self.testcases_ok[0])
        p = OPCProperty(*self.testcases_ok[0])


class OPCOperationTest(unittest.TestCase, OPCOperation):
    ''' Test OPCOperations '''

    O_ReplyBase = {'RcvTime' : datetime.datetime(2006, 2, 15, 12, 0, 0),
                   'ReplyTime' : datetime.datetime(2006, 2, 15, 12, 15, 18),
                   'ClientRequestHandle' : 'TestHandle1',
                   'RevisedLocaleID' : 'en',
                   'ServerState' : 'running'}


    O_RequestOptions = {'ReturnErrorText' : True,
                        'ReturnDiagnosticInfo' : True,
                        'ReturnItemTime' : True,
                        'ReturnItemPath' : True,
                        'ReturnItemName' : True,
                        'RequestDeadline' : datetime.datetime(2006, 2, 15,
                                                              12, 25, 18),
                        'ClientRequestHandle' : 'RequestTestHandle01',
                        'LocaleID' : 'de'}


    I_Property1 =  OPCProperty(Name='value',
                               Value=1,
                               Description='Item Value',
                               ItemPath='X',
                               ItemName='Lightswitch1')
    I_Property2 =  OPCProperty(Name='accessRights',
                               Value='w',
                               ItemName='Lightswitch2',
                               ResultID=OPCBasic.OPC_E_BUSY,
                               ErrorText='Server Busy')
    
    I_Property3 =  OPCProperty(Name=QName('bla:qua','MySuperProperty'),
                               Value='foobar',
                               ResultID=OPCBasic.OPC_E_FAIL,
                               ErrorText='Server Failed')
    
    I_Property4 =  OPCProperty(Name='description',
                               Value='Blabla')

    def del_empty_iter(self,d):
        ''' Delete empty dictionaries and tuples from dict d '''
        for k,v in d.items():
            if (v == []) or (v == ()):
                del d[k]

    def checkempty(self,rilist,rOptions,ODefaults):
        ''' Empty Test '''
        # Delete empty sequences from dictionaries, such as [] and ()
        self.del_empty_iter(rOptions)
        diffres = cmp_dict_list(ODefaults,rOptions)
        self.failUnless(diffres == '',
                        'Empty Test: Options dictionaries differ: \n'+\
                        diffres)
        self.assertEqual([],rilist)
    

    def checkfull(self,rilist,rOptions,ilist,ODefaults,sw,psw):
        # Check general Options
        # Check if all Options can be found in the SOAP message            

        for item in expanddict(ODefaults):
            self.failIf((sw.find(tosoapstr(item)) == -1),
                        'Missing item in serialized SOAP message:\n'+\
                        psw+'\nMissing OptionsItem:'+str(item))
        
        # Check if dictionaries match
        diffres = cmp_dict_list(ODefaults,rOptions)
        self.failUnless(diffres == '',
                        psw+'\n'+ 'Filled Test:'+\
                        'Options dictionaries differ: \n'+\
                        diffres)

        # Check Items
        # results with different order should not raise errors
        ilist.sort()
        rilist.sort()

        # Both ItemLists have to have the sames length
        self.assertEqual(len(ilist),len(rilist))
        # Now iterate over items and compare them
        for i in range(len(ilist)):
            # Check if ItemContainer attributes exist in SOAP message
            for item in expanddict(ilist[i].__dict__):
                if item == 'ErrorText':
                    # This Element is called "Text" in the SOAP message
                    item = 'Text'
                if item != None:
                    self.failIf((sw.find(tosoapstr(item)) == -1),
                                'Missing item in serialized SOAP message:\n'+\
                                psw+'\nMissing ItemContainer Item:'+\
                                tosoapstr(item))
            
            diffres = cmp_dict_list(ilist[i].__dict__,rilist[i].__dict__)
            self.failUnless(diffres == '',
                            psw+'\n'+
                            'Filled Test: Item differs: \n'+\
                            diffres)


    def dotest(self,op,ilist,Options,ODefaults):
        ''' bla no test? '''
        if op.find('Response') > 0:
            msg = op[:-8]+'SoapOut'
        else:
            msg = op+'SoapIn'

        tcmsg = getattr(OpcXmlDaSrv_services,msg)
        tc = tcmsg()
        fillfunc = self.fill_tc
        readfunc = self.read_tc
        
        # try with empty ilist and empty options
        fillfunc(tc,[],{})
        rilist,rOptions = readfunc(tc)
        self.checkempty(rilist,rOptions,ODefaults)

        # Now serialize and parse it and check again
        # Serialize typecode into string
        sw = str(ZSI.SoapWriter().serialize(tc,unique=True))
        ps = ZSI.ParsedSoap(sw)
        tc = ps.Parse(tc.typecode)
        rilist,rOptions = readfunc(tc)
        self.checkempty(rilist,rOptions,ODefaults)

        # Copy Options for filling
        fillOptions = dict(Options)
        # Now add some dummy Option which should come back
        fillOptions.update({'NoSuchOptionXYZ' : 'Does not exist!'})
        
        # Now try with all given Options and ItemContainers
        fillfunc(tc,copy.deepcopy(ilist),fillOptions)

        # Dummy option should come back again
        self.failUnless(fillOptions.has_key('NoSuchOptionXYZ'))

        # Serialize typecode into string
        sw = str(ZSI.SoapWriter().serialize(tc,unique=True))
        psw=xml.dom.minidom.parseString(sw).toprettyxml()

        ODefaults.update(Options)
        # Correct "ReqType"
        if ODefaults.has_key('ReqType'):
            ODefaults['ReqType'] = python2xsd(ODefaults['ReqType'])
        for i in range(len(ilist)):
            v = ilist[i].__dict__.get('ReqType',None)
            if v != None:
                ilist[i].__dict__['ReqType'] = python2xsd(v)

        # Make a copy
        TOptions = dict(ODefaults)

        rilist,rOptions = readfunc(tc)
        self.checkfull(rilist,rOptions,ilist,TOptions,sw,psw)

        # parse it and check again
        ps = ZSI.ParsedSoap(sw)
        tc = ps.Parse(tc.typecode)
        rilist,rOptions = readfunc(tc)
        TOptions = dict(ODefaults)
        self.checkfull(rilist,rOptions,ilist,TOptions,sw,psw)


    def testGetStatus(self):
        ''' Test GetStatus Message '''
        Options = {'LocaleID': 'en-us',
                   'ClientRequestHandle' : 'abc'
                   }
        ilist = []
        self.dotest('GetStatus',ilist,Options,{})

    def testGetStatusResponse(self):
        ''' Test GetStatus Response Message '''
        Options = {'StatusInfo' : 'TestStatus',
                   'VendorInfo' : 'MyUnitTest',
                   'SupportedLocaleIDs' : ['en','de'],
                   'SupportedInterfaceVersions' : ['XML_DA_Version_1_0'],
                   'StartTime' : datetime.datetime(2006, 2, 15, 13, 59, 10),
                   'ProductVersion' : 'TestTest123'}
        
        ilist = []
        Options.update(self.O_ReplyBase)
        self.dotest('GetStatusResponse',ilist,Options,{})

        # Try high precision time with timezone
        #Options['RcvTime'] = '2006-01-03T10:56:00.6875000-05:00'
        #self.dotest('GetStatusResponse',ilist,Options,{},{})

    def testRead(self):
        ''' Test Read Message '''
        Options = {'ItemPath' : 'TestPath1',
                   'ReqType' : '',
                   'MaxAge' : 123}
        ilist = []
        Options.update(self.O_RequestOptions)
        ilist.append(ItemContainer(ItemPath='TestPath2',
                                   ReqType='',
                                   ItemName='TestIName1',
                                   ClientItemHandle='Handle123',
                                   MaxAge=234))
        ilist.append(ItemContainer(ItemPath='TestPath3',
                                   ReqType=0,
                                   ItemName='TestIName2',
                                   ClientItemHandle='Handle223',
                                   MaxAge=235))

        self.dotest('Read',ilist,Options,{})

    def testReadResponse(self):
        ''' Test Read Response Message '''
        Options = {}
        Options.update(self.O_ReplyBase)
        ilist1 = [ItemContainer(DiagnosticInfo='diagnose1',
                                Value='Hello, World!',
                                QualityField='bad',
                                LimitField='none',
                                VendorField=123,
                                ValueTypeQualifier=(NS_XSD,'date'),
                                ItemPath='MyItemPath3',
                                ItemName='MyItemName1',
                                ClientItemHandle='MyHandle123',
                                Timestamp=datetime.datetime(2006, 2, 15,
                                                            13, 59, 1),
                                ResultID=OPCBasic.OPC_E_FAIL,
                                ErrorText='TestError123'),
                  ItemContainer(DiagnosticInfo='diagnose2',
                                Value='Hello, World 2!',
                                QualityField='bad',
                                LimitField='none',
                                VendorField=123,
                                ValueTypeQualifier=(NS_XSD,'date'),
                                ItemPath='MyItemPath2',
                                ItemName='MyItemName2',
                                ClientItemHandle='MyHandle124',
                                Timestamp=datetime.datetime(2006, 2, 15,
                                                            13, 39, 1),
                                ResultID=OPCBasic.OPC_E_BUSY,
                                ErrorText='TestError125')]
        self.dotest('ReadResponse',ilist1,Options,{})
        # FIXME ReadResponse should be tested with all available data types
        # xsd:string
        self.dotest('ReadResponse',
                    [ItemContainer(Value='abc')],
                    Options,{})
        # xsd:boolean
        self.dotest('ReadResponse',
                    [ItemContainer(Value=True)],
                    Options,{})
        # xsd:double (including xsd:float)
        self.dotest('ReadResponse',
                    [ItemContainer(Value=12.45)],
                    Options,{})
        # FIXME xsd:decimal
        #self.dotest('ReadResponse',
        #            [ItemContainer(Value=decimal.Decimal('22.44'))],
        #            Options,{})
        # xsd:long (including xsd:int/xsd:short/xsd:byte and all unsigneds)
        self.dotest('ReadResponse',
                    [ItemContainer(Value=1279)],
                    Options,{})
        # FIXME xsd: base64Binary - don't know what to do about this?
        #self.dotest('ReadResponse',
        #            [ItemContainer(Value=???)],
        #            Options,{})
        # xsd:dateTime FIXME: fractions of seconds
        self.dotest('ReadResponse',
                    [ItemContainer(Value=datetime.datetime(2006, 2, 15,
                                                           13, 59, 1))],
                    Options,{})
        # FIXME xsd:date
        #self.dotest('ReadResponse',
        #            [ItemContainer(Value=datetime.date(2006, 2, 15))],
        #            Options,{})
        # FIXME xsd:time
        #self.dotest('ReadResponse',
        #            [ItemContainer(Value=datetime.time(13, 59, 1))],
        #            Options,{})
        # FIXME xsd:duration
        #self.dotest('ReadResponse',
        #            [ItemContainer(Value=datetime.timedelta(1000))],
        #            Options,{})
        # xsd:QName
        self.dotest('ReadResponse',
                    [ItemContainer(Value=QNameValue('urn:bla','ABC'))],
                    Options,{})
        # ArrayOfInt (including ArrayOfByte/Short + Unsigned variants)
        self.dotest('ReadResponse',
                    [ItemContainer(Value=[1,2,3])],
                    Options,{})
        # Try with only one element
        self.dotest('ReadResponse',
                    [ItemContainer(Value=[1])],
                    Options,{})
        # ArrayOfLong 
        self.dotest('ReadResponse',
                    [ItemContainer(Value=[1234234234234234,2342342342323423])],
                    Options,{})
        # ArrayOfDouble (including ArrayOfFloat)
        self.dotest('ReadResponse',
                    [ItemContainer(Value=[1.1,23.346])],
                    Options,{})
        # FIXME: ArrayOfDecimal
        # ArrayOfBoolean
        self.dotest('ReadResponse',
                    [ItemContainer(Value=[True,False])],
                    Options,{})
        # ArrayOfString
        self.dotest('ReadResponse',
                    [ItemContainer(Value=['abc','def','jkl','wf'])],
                    Options,{})
        # FIXME ArrayOfDateTime - waiting for native datetime ZSI implement
        #self.dotest('ReadResponse',
        #            [ItemContainer(Value=[datetime.datetime(2006, 2, 15,
        #                                                   13, 59, 1),
        #                                  datetime.datetime(2006, 3, 15,
        #                                                   13, 59, 1)])],
        #            Options,{})
        # FIXME ArrayOfAnyType - Arrays that contain arbitrary data types
        #                        or other arrays
        self.dotest('ReadResponse',
                    [ItemContainer(Value=[1,'def',2.2,True])],
                    Options,{})
        
        
        # Empty Value
        ilist3 = [ItemContainer(ItemName='')]
        self.dotest('ReadResponse',ilist3,Options,{})

    def testWrite(self):
        ''' Test Write Message '''
        Options = {}
        Options.update(self.O_RequestOptions)
        ilist = []
        ODefault = {'ReturnValuesOnReply' : False}
        ilist = [ItemContainer(DiagnosticInfo='diagnose1',
                               Value='Hello, World!',
                               QualityField='bad',
                               LimitField='none',
                               VendorField=123,
                               ValueTypeQualifier=(NS_XSD,'date'),
                               ItemPath='MyItemPath1',
                               ItemName='MyItemName1',
                               ClientItemHandle='MyHandle123',
                               Timestamp=datetime.datetime(2006, 2, 15,
                                                           13, 59, 1)),
                 ItemContainer(DiagnosticInfo='diagnose2',
                               Value='Hello, World 2!',
                               QualityField='bad',
                               LimitField='none',
                               VendorField=123,
                               ValueTypeQualifier=(NS_XSD,'date'),
                               ItemPath='MyItemPath2',
                               ItemName='MyItemName2',
                               ClientItemHandle='MyHandle124',
                               Timestamp=datetime.datetime(2006, 2, 15,
                                                           13, 39, 1))]
        self.dotest('Write',ilist,Options,ODefault)

    def testWriteResponse(self):
        ''' Test Write Response Message '''
        Options = {}
        Options.update(self.O_ReplyBase)
        ilist = [ItemContainer(DiagnosticInfo='diagnose1',
                               Value='Hello, World!',
                               QualityField='bad',
                               LimitField='none',
                               VendorField=123,
                               ValueTypeQualifier=(NS_XSD,'date'),
                               ItemPath='MyItemPath1',
                               ItemName='MyItemName1',
                               ClientItemHandle='MyHandle123',
                               Timestamp=datetime.datetime(2006, 2, 15,
                                                           13, 59, 12),
                               ResultID=OPCBasic.OPC_E_FAIL,
                               ErrorText='TestError123'),
                 ItemContainer(DiagnosticInfo='diagnose2',
                               Value='Hello, World 2!',
                               QualityField='bad',
                               LimitField='none',
                               VendorField=123,
                               ValueTypeQualifier=(NS_XSD,'date'),
                               ItemPath='MyItemPath2',
                               ItemName='MyItemName2',
                               ClientItemHandle='MyHandle124',
                               Timestamp=datetime.datetime(2006, 2, 15,
                                                           13, 39, 1),
                               ResultID=OPCBasic.OPC_E_BUSY,
                               ErrorText='TestError125')]
        
        self.dotest('WriteResponse',ilist,Options,{})

    def testSubscribe(self):
        ''' Test Subscribe Message '''
        Options = {'ReturnValuesOnReply' : True,
                   'SubscriptionPingRate' : 10,
                   'ItemPath': 'MyPath123',
                   'ReqType' : '',
                   'Deadband' : 12.2,
                   'RequestedSamplingRate' : 23,
                   'EnableBuffering' : True}
        Options.update(self.O_RequestOptions)
        ilist = [ItemContainer(ItemPath='MyItemPath1',
                               ReqType=123,
                               ItemName='MyItemName1',
                               ClientItemHandle='MyHandle123',
                               Deadband=34.3,
                               RequestedSamplingRate=50,
                               EnableBuffering=False),
                 ItemContainer(ItemPath='MyItemPath2',
                               ReqType=124,
                               ItemName='MyItemName2',
                               ClientItemHandle='MyHandle223',
                               Deadband=34.4,
                               RequestedSamplingRate=51,
                               EnableBuffering=True)]
        ODefault = {'ReturnValuesOnReply' : False}
        self.dotest('Subscribe',ilist,Options,ODefault)

    def testSubscribeResponse(self):
        ''' Test Subscribe Response Message '''
        Options = {'ServerSubHandle' : 'subhandle123',
                   'RevisedSamplingRate' : 295}
        Options.update(self.O_ReplyBase)
        ilist = [ItemContainer(DiagnosticInfo='diagnose1',
                               Value='Hello, World!',
                               QualityField='bad',
                               LimitField='none',
                               VendorField=123,
                               ValueTypeQualifier=(NS_XSD,'date'),
                               ItemPath='MyItemPath1',
                               ItemName='MyItemName1',
                               ClientItemHandle='MyHandle123',
                               Timestamp=datetime.datetime(2006, 2, 15,
                                                           13, 59, 1),
                               ResultID=OPCBasic.OPC_E_FAIL,
                               ErrorText='TestError123',
                               RevisedSamplingRate=131),
                 ItemContainer(DiagnosticInfo='diagnose2',
                               Value='Hello, World 2!',
                               QualityField='bad',
                               LimitField='none',
                               VendorField=123,
                               ValueTypeQualifier=(NS_XSD,'date'),
                               ItemPath='MyItemPath2',
                               ItemName='MyItemName2',
                               ClientItemHandle='MyHandle124',
                               Timestamp=datetime.datetime(2006, 2, 15,
                                                           13, 39, 1),
                               ResultID=OPCBasic.OPC_E_BUSY,
                               ErrorText='TestError125',
                               RevisedSamplingRate=13)]
        Options.update(self.O_ReplyBase)
        self.dotest('SubscribeResponse',ilist,Options,{})

    def testSubscriptionPolledRefresh(self):
        ''' Test SubscriptionPolledRefresh Message '''
        Options = {'ServerSubHandles' : ['subhandle123', 'subhandle456'],
                   'HoldTime' : datetime.datetime(2006, 2, 15, 13, 59, 1),
                   'WaitTime' : 100,
                   'ReturnAllItems' : True}
        Options.update(self.O_RequestOptions)
        ilist = []
        self.dotest('SubscriptionPolledRefresh',ilist,Options,{})

    def testSubscriptionPolledRefreshResponse(self):
        ''' Test SubscriptionPolledRefresh Response Message '''
        Options = {'InvalidServerSubHandles' : ['InvalidSub1', 'InvalidSub2'],
                   'DataBufferOverflow' : True}
        Options.update(self.O_ReplyBase)
        ilist = [ItemContainer(DiagnosticInfo='diagnose1',
                               Value='Hello, World!',
                               QualityField='bad',
                               LimitField='none',
                               VendorField=123,
                               ValueTypeQualifier=(NS_XSD,'date'),
                               ItemPath='MyItemPath1',
                               ItemName='MyItemName1',
                               ClientItemHandle='MyHandle123',
                               Timestamp=datetime.datetime(2006, 2, 15,
                                                           13, 39, 1),
                               ResultID=OPCBasic.OPC_E_FAIL,
                               ErrorText='TestError123',
                               SubscriptionHandle='SubHandleA'),
                 ItemContainer(DiagnosticInfo='diagnose2',
                               Value='Hello, World 2!',
                               QualityField='bad',
                               LimitField='none',
                               VendorField=123,
                               ValueTypeQualifier=(NS_XSD,'date'),
                               ItemPath='MyItemPath2',
                               ItemName='MyItemName2',
                               ClientItemHandle='MyHandle124',
                               Timestamp=datetime.datetime(2006, 2, 15,
                                                           13, 49, 1),
                               ResultID=OPCBasic.OPC_E_BUSY,
                               ErrorText='TestError125',
                               SubscriptionHandle='SubHandleA'),
                 ItemContainer(DiagnosticInfo='diagnose3',
                               Value='Hello, World 3!',
                               QualityField='bad',
                               LimitField='none',
                               VendorField=123,
                               ValueTypeQualifier=(NS_XSD,'date'),
                               ItemPath='MyItemPath3',
                               ItemName='MyItemName3',
                               ClientItemHandle='MyHandle126',
                               Timestamp=datetime.datetime(2006, 2, 15,
                                                           13, 19, 1),
                               ResultID=OPCBasic.OPC_E_BUSY,
                               ErrorText='TestError125',
                               SubscriptionHandle='SubHandleB')
                 ]
        Options.update(self.O_ReplyBase)
        self.dotest('SubscriptionPolledRefreshResponse',ilist,Options,{})

    def testSubscriptionCancel(self):
        ''' Test SubscriptionCancel Message '''
        Options = {'ServerSubHandle' : '12345',
                   'ClientRequestHandle' : 'abebu'}
        ilist = []
        self.dotest('SubscriptionCancel',ilist,Options,{})

    def testSubscriptionCancelResponse(self):
        ''' Test SubscriptionCancel Response Message '''
        Options = {'ClientRequestHandle' : 'adbebu'}
        ilist = []
        self.dotest('SubscriptionCancelResponse',ilist,Options,{})

    def testBrowse(self):
        ''' Test Browse Message '''
        Options = {'LocaleID' : 'en',
                   'ClientRequestHandle' : 'Handlebla',
                   'ItemPath' : 'MyPath1',
                   'ItemName' : 'MyName1',
                   'ContinuationPoint' : 'ContPoint1',
                   'MaxElementsReturned' : 100,
                   'BrowseFilter' : 'all',
                   'ElementNameFilter' : 'abebu',
                   'VendorFilter' : 'quabla',
                   'ReturnAllProperties' : True,
                   'ReturnPropertyValues' : True,
                   'ReturnErrorText' : True,
                   'PropertyNames' : [QName(NS_XDA,'euType'),
                                      QName(NS_XDA,'accessRights')]}
        ilist = []
        self.dotest('Browse',ilist,Options,{})

    def testBrowseResponse(self):
        ''' Test Browse Response Message '''
        Options = {'ContinuationPoint' : 'ContPoint2',
                   'MoreElements' : True}
        Options.update(self.O_ReplyBase)
        item1=ItemContainer(Name='itname1',
                               ItemPath='myPath1',
                               ItemName='myName1',
                               IsItem = True,
                               HasChildren = False)
        # Add Properties
        item1.addProperty(self.I_Property1)
        item1.addProperty(self.I_Property2)
        item2=ItemContainer(Name='itname2',
                               ItemPath='myPath2',
                               ItemName='myName2',
                               IsItem = True,
                               HasChildren = False)
        # Add Properties
        item2.addProperty(self.I_Property3)
        item2.addProperty(self.I_Property4)

        ilist = [item1,item2]
        self.dotest('BrowseResponse',ilist,Options,{})

    def testGetProperties(self):
        ''' Test GetProperties Message '''
        Options = {'LocaleID' : 'br',
                   'ClientRequestHandle' : 'Mysuperhandle123',
                   'ItemPath' : 'MyTestPath456',
                   'ReturnAllProperties' : True,
                   'ReturnPropertyValues' : False,
                   'ReturnErrorText' : True,
                   'PropertyNames' : [QName(NS_XDA,'euType'),
                                      QName(NS_XDA,'accessRights')]
                   }
        ilist = [ItemContainer(ItemName='MyName1',
                               ItemPath='MyPath1'),
                 ItemContainer(ItemName='MyName2',
                               ItemPath='MyPath2')]
        
        self.dotest('GetProperties',ilist,Options,{})

    def testGetPropertiesResponse(self):
        ''' Test GetProperties Response Message '''
        Options = {}
        Options.update(self.O_ReplyBase)
        item1 = ItemContainer(ItemPath='MySamplePath1',
                              ItemName='MySampleName1',
                              ResultID=OPCBasic.OPC_E_BUSY,
                              ErrorText='Server Busy')
        # Add Properties
        item1.addProperty(self.I_Property1)
        item1.addProperty(self.I_Property2)
        item2=ItemContainer(ItemPath='MySamplePath2',
                            ItemName='MySampleName2',
                            ResultID=OPCBasic.OPC_E_FAIL,
                            ErrorText='Server Failed')
        # Add Properties
        item2.addProperty(self.I_Property3)
        item2.addProperty(self.I_Property4)
        ilist = [item1,item2]
        self.dotest('GetPropertiesResponse',ilist,Options,{})

    #del testGetStatus
    #del testGetStatusResponse
    #del testRead
    #del testReadResponse
    #del testWrite
    #del testWriteResponse
    #del testSubscribe
    #del testSubscribeResponse
    #del testSubscriptionPolledRefresh
    #del testSubscriptionPolledRefreshResponse
    #del testSubscriptionCancel
    #del testSubscriptionCancelResponse
    #del testBrowse
    #del testBrowseResponse
    #del testGetProperties
    #del testGetPropertiesResponse
    
#del xsd2pythonCheck
#del ItemContainerCheck
#del OPCPropertyCheck
#del QNameValueCheck

if __name__ == '__main__':
    unittest.main()
