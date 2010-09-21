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
''' Utility functions and definitions for OPC '''
import decimal,time,datetime

import ZSI
import ZSI.fault
from ZSI.TC import RegisterType
from ZSI.TC import _get_type_definition

from OpcXmlDaSrv_services import *

class XSDTypeError(TypeError):
    pass

class OPCServerError(ZSI.Fault):
    pass

# XML Schema
NS_XSD = 'http://www.w3.org/2001/XMLSchema'
# XML Schema-Instance
NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'
# ZSI Namespace
NS_ZSI = 'http://www.zolera.com/schemas/ZSI/'
# XMLDA Namespace
NS_XDA = 'http://opcfoundation.org/webservices/XMLDA/1.0/'
# PyOPC Namespace
NS_PYO = 'http://qwer.tk/PyOPC/'

# Do some ZSI specifics
# Create some TypeDefinitions, so that Arrays can be serialized
ArrayOfInt=ZSI.TC._get_type_definition(NS_XDA,
                                       "ArrayOfInt")('Value').pyclass
ArrayOfLong=ZSI.TC._get_type_definition(NS_XDA,
                                        "ArrayOfLong")('Value').pyclass
ArrayOfDouble=ZSI.TC._get_type_definition(NS_XDA,
                                          "ArrayOfDouble")('Value').pyclass
ArrayOfDecimal=ZSI.TC._get_type_definition(NS_XDA,
                                          "ArrayOfDecimal")('Value').pyclass
ArrayOfBoolean=ZSI.TC._get_type_definition(NS_XDA,
                                           "ArrayOfBoolean")('Value').pyclass
ArrayOfString=ZSI.TC._get_type_definition(NS_XDA,
                                          "ArrayOfString")('Value').pyclass
ArrayOfDateTime=ZSI.TC._get_type_definition(NS_XDA,
                                            "ArrayOfDateTime")('Value').pyclass
ArrayOfAnyType=ZSI.TC._get_type_definition(NS_XDA,
                                           "ArrayOfAnyType")('Value').pyclass

# Register QNames, so that they can be parsed in the AnyType
RegisterType(ZSI.TC.QName, minOccurs=0)

# This comes from the Python cookbook, page 240 or also
# http://herlock.com/ob/pythoncb/0596007973/chp-6-sect-3.html
def no_new_attributes(wrapped_setattr):
    """ raise an error on attempts to add a new attribute, while
        allowing existing attributes to be set to new values.
    """
    def __setattr__(self, name, value):
        if hasattr(self, name) or name in ('__implemented__',
                                           '__providedBy__',
                                           '__provides__'):
            # not a new attribute, allow setting
            # __implemented__ etc. attributes are for twisted-trial unittesting
            wrapped_setattr(self, name, value)
        else:                      # a new attribute, forbid adding it
            raise AttributeError("can't add attribute %r to %s" % (name, self))
    return __setattr__
class NoNewAttrs(object):
    """ subclasses of NoNewAttrs inhibit addition of new attributes, while
        allowing existing attributed to be set to new values.
    """
    # block the addition new attributes to instances of this class
    __setattr__ = no_new_attributes(object.__setattr__)
    class __metaclass__(type):
        "simple custom metaclass to block adding new attributes to this class"
        __setattr__ = no_new_attributes(type.__setattr__)

def python2xsd(var):
    ''' Function that returns xsd-schemas for given objects '''
    
    trans=((basestring,'string','String'),
           (bool,'boolean','Boolean'),
           (int,'int','Int'),
           (long,'long','Long'),
           (float,'double','Double'),
           (decimal.Decimal,'decimal','Decimal'),
           (datetime.datetime,'dateTime','DateTime'),
           (QNameValue,'QName',None),
           (datetime.time,'time',None),
           (datetime.date,'date',None),
           (datetime.timedelta,'duration',None))

    if isinstance(var,type):
        # somebody did a python2xsd(type(var))
        for t in trans:
            if issubclass(var,t[0]):
                return (NS_XSD,t[1])
        # Unknown type, hence raise TypeError
        raise XSDTypeError('Type %s cannot be mapped to XML Schema type' \
                        % var)

    if isinstance(var,(list,)):
        # A list/tuple with items is given
        if len(var) == 0:
            # Empty list/tuple, return None
            raise XSDTypeError('Empty Lists/Tuples cannot be mapped')

        resdict = {}
        transcount = 0
        for v in var:
            if isinstance(v,(list,tuple)):
                # The list contains another list
                # Hence it must be ArrayOfAnyType
                return (NS_XDA,'ArrayOfAnyType')
            else:
                for t in trans:
                    if isinstance(v,t[0]):
                        if t[2] == None:
                            # Seems to be time/date/duration 
                            raise XSDTypeError('Type %s cannot be mapped'
                                               'to OPCArray type' % type(t))
                        else:
                            # Append this to resdict
                            resdict[(NS_XDA,'ArrayOf'+t[2])] = None
                            transcount += 1
                            # Break loop as bool will be counted double
                            break
        # Raise error if not all list items could be mapped
        if len(var) != transcount:
            raise XSDTypeError('The array contains unknown datatypes') 
        if len(resdict) == 1:
            # The list contains only the same type, hence return it
            return resdict.keys()[0]
        else:
            # The list contains different data types
            return (NS_XDA,'ArrayOfAnyType')
                
    # Test parameter "var" directly
    for t in trans:
        if isinstance(var,t[0]):
            return (NS_XSD,t[1])

    # Everything failed, raise an error
    raise XSDTypeError('Type %s cannot be mapped to XML Schema type' \
                    % type(var))


def extr_soap_type(tc):
    ''' Returns the element tag name a typecode represents
    Probably an xsi:complex type '''
    buf = str(tc.typecode)
    # Has the following format:
    # '<OpcXmlDaSrv_services_types.ItemValue_Def object at 0x407f87cc>'
    # Therefore strip everything left before '.' and right after '_'
    buf = buf[buf.index('types.')+6:buf.rindex('_')]
    return buf

class QName(tuple):

    def _getURI(self):
        return self[0]
    def _getname(self):
        return self[1]
    
    URI = property(_getURI)
    name = property(_getname)
    
    def __new__(cls, URI, name):
        ''' Check vor valid URI and create tuple '''
        if not isinstance(URI,basestring) or \
               not isinstance(name,basestring):
            raise TypeError('Parameters must be strings')
        if ':' not in URI:
            raise ValueError("First argument is no URI: %s" % str(URI))
        return tuple.__new__(cls, (URI,name))
    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__,self.URI, self.name)
    def __copy__(self):
        return self
    def __deepcopy__(self, visit):
        return self


class QNameValue(QName):
    ''' A QName (qualified name) Value '''
    typecode = ZSI.TC.QName('Value')
        
OPCProperties = {'dataType' : 'ItemCanonical Data Type',
                 'value' : 'Item Value',
                 'quality' : 'Item Quality',
                 'timestamp' : 'Item Timestamp',
                 'accessRights' : 'Item Access Rights',
                 'scanRate' : 'Server Scan Rate',
                 'euType' : 'Item EU Type',
                 'euInfo' : 'Item EUInfo',
                 'engineeringUnits' : 'EU Units',
                 'description' : 'Item Description',
                 'highEU' : 'High EU',
                 'lowEU' : 'Low EU',
                 'highIR' : 'High Instrument Range',
                 'lowIR' : 'Low Instrument Range',
                 'closeLabel' : 'Contact Close Label',
                 'openLabel' : 'Contact Open Label',
                 'timeZone' : 'Item Timezone',
                 'minimumValue' : 'Minimum Value',
                 'maximumValue' : 'Maxmimum Value',
                 'valuePrecision' : 'Value Precision'}


class OPCProperty(object):
    ''' Class that holds "Property tuples" with named elements:
    (Value,Description,ItemPath,ItemName,ResultID,ErrorText)'''

    PTuple = ('Name',
              'Value',
              'Description',
              'ItemPath',
              'ItemName',
              'ResultID',
              'ErrorText')
    
    def __init__(self,*args,**kwds):
        ''' Add all arguments as attributes '''
        args = list(args)
        # Extend list to len of PTuple
        args.extend([None]*(len(self.PTuple)-len(args)))
        # Set object attributes to either given value or to None
        for attr,arg in zip(self.PTuple,args):
            setattr(self,attr,arg)
        # Now override attributes with eventually given name parameters
        for key,val in kwds.items():
            if key in self.PTuple:
                setattr(self,key,val)
            else:
                raise AttributeError('Invalid attribute: %s' % key)
        if self.Name:
            if isinstance(self.Name,basestring):
                # Build a QName from a string
                if OPCProperties.has_key(self.Name):
                    # Maybe the property is an OPC property?
                    self.Name = QName(NS_XDA,self.Name)
                else:
                    # Use the PyOPC namespace
                    self.Name = QName(NS_PYO,self.Name)
        # Call the superclass's setval method
        # Now add description if not assigned
        if self.Description == None:
            if self.Name:
                if self.Name.URI == NS_XDA:
                    self.Description = OPCProperties.get(self.Name.name,None)
    def __repr__(self):
        return ('%s(%r, %r, %r, %r, %r, %r, %r)' % \
                (self.__class__.__name__,
                 self.Name,
                 self.Value,
                 self.Description,
                 self.ItemPath, self.ItemName,
                 self.ResultID, self.ErrorText))
    def __str__(self):
        return ('%s(Name=%r, Value=%r, Description=%r, ItemPath=%r, '\
                'ItemName=%r, ResultID=%r, ErrorText=%r)' % \
                (self.__class__.__name__,
                 self.Name,
                 self.Value,
                 self.Description,
                 self.ItemPath, self.ItemName,
                 self.ResultID, self.ErrorText))
    def __iter__(self):
        for name in self.PTuple:
            yield getattr(self,name)


def IsCritical(errcode):
    ''' Reports if an OPC error/exception is critical or not
    (e.g. if it is a Success Code S_XXX or Error Code E_XXX'''

    if errcode == None:
        # There is no recorded error
        return False
    elif errcode[1][:2] == 'S_':
        return False
    elif errcode[1][:2] == 'E_':
        return True
    else:
        # No known errorcode, raise exception
        raise TypeError('Errorcode %s is invalid' % errcode[1])

def mkItemKey(Item):
    ''' Create Key from ItemName/ItemPath of an OPC item '''
    key = ''
    if Item.ItemPath:
        key += Item.ItemPath
    if Item.ItemName:
        key += Item.ItemName
    return key

def print_options((ilist,Options)):
    for key, value in Options.items():
        if value:
            print key,':',value
    for item in ilist:
        for key, value in item.__dict__.items():
            if value:
                print '  ',key,':',value
        print '  --'
    print
