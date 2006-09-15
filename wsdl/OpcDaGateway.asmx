<?xml version="1.0" encoding="utf-8"?>
<wsdl:definitions xmlns:http="http://schemas.xmlsoap.org/wsdl/http/" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:s="http://www.w3.org/2001/XMLSchema" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:tns="http://opcfoundation.org/webservices/XMLDA/1.0/" xmlns:tm="http://microsoft.com/wsdl/mime/textMatching/" xmlns:mime="http://schemas.xmlsoap.org/wsdl/mime/" targetNamespace="http://opcfoundation.org/webservices/XMLDA/1.0/" xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/">
  <wsdl:types>
    <s:schema elementFormDefault="qualified" targetNamespace="http://opcfoundation.org/webservices/XMLDA/1.0/">
      <s:element name="GetProperties">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="unbounded" name="ItemIDs" type="tns:ItemIdentifier" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="PropertyNames" type="s:QName" />
          </s:sequence>
          <s:attribute name="LocaleID" type="s:string" />
          <s:attribute name="ClientRequestHandle" type="s:string" />
          <s:attribute name="ItemPath" type="s:string" />
          <s:attribute default="false" name="ReturnAllProperties" type="s:boolean" />
          <s:attribute default="false" name="ReturnPropertyValues" type="s:boolean" />
          <s:attribute default="false" name="ReturnErrorText" type="s:boolean" />
        </s:complexType>
      </s:element>
      <s:complexType name="ItemIdentifier">
        <s:attribute name="ItemPath" type="s:string" />
        <s:attribute name="ItemName" type="s:string" />
      </s:complexType>
      <s:element name="GetPropertiesResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="GetPropertiesResult" type="tns:ReplyBase" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="PropertyLists" type="tns:PropertyReplyList" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="Errors" type="tns:OPCError" />
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:complexType name="ReplyBase">
        <s:attribute name="RcvTime" type="s:dateTime" use="required" />
        <s:attribute name="ReplyTime" type="s:dateTime" use="required" />
        <s:attribute name="ClientRequestHandle" type="s:string" />
        <s:attribute name="RevisedLocaleID" type="s:string" />
        <s:attribute name="ServerState" type="tns:serverState" use="required" />
      </s:complexType>
      <s:simpleType name="serverState">
        <s:restriction base="s:string">
          <s:enumeration value="running" />
          <s:enumeration value="failed" />
          <s:enumeration value="noConfig" />
          <s:enumeration value="suspended" />
          <s:enumeration value="test" />
          <s:enumeration value="commFault" />
        </s:restriction>
      </s:simpleType>
      <s:complexType name="PropertyReplyList">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="Properties" type="tns:ItemProperty" />
        </s:sequence>
        <s:attribute name="ItemPath" type="s:string" />
        <s:attribute name="ItemName" type="s:string" />
        <s:attribute name="ResultID" type="s:QName" use="required" />
      </s:complexType>
      <s:complexType name="ItemProperty">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="1" name="Value" />
        </s:sequence>
        <s:attribute name="Name" type="s:QName" use="required" />
        <s:attribute name="Description" type="s:string" />
        <s:attribute name="ItemPath" type="s:string" />
        <s:attribute name="ItemName" type="s:string" />
        <s:attribute name="ResultID" type="s:QName" use="required" />
      </s:complexType>
      <s:complexType name="OPCError">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="1" name="Text" type="s:string" />
        </s:sequence>
        <s:attribute name="ID" type="s:QName" use="required" />
      </s:complexType>
      <s:complexType name="ArrayOfDouble">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="double" type="s:double" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfUnsignedShort">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="unsignedShort" type="s:unsignedShort" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfDateTime">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="dateTime" type="s:dateTime" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfAnyType">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="anyType" nillable="true" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfDecimal">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="decimal" type="s:decimal" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfByte">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="byte" type="s:byte" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfShort">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="short" type="s:short" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfBoolean">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="boolean" type="s:boolean" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfString">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="string" nillable="true" type="s:string" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfFloat">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="float" type="s:float" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfInt">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="int" type="s:int" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfUnsignedInt">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="unsignedInt" type="s:unsignedInt" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfLong">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="long" type="s:long" />
        </s:sequence>
      </s:complexType>
      <s:complexType name="ArrayOfUnsignedLong">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="unsignedLong" type="s:unsignedLong" />
        </s:sequence>
      </s:complexType>
      <s:element name="Subscribe">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="Options" type="tns:RequestOptions" />
            <s:element minOccurs="0" maxOccurs="1" name="ItemList" type="tns:SubscribeRequestItemList" />
          </s:sequence>
          <s:attribute name="ReturnValuesOnReply" type="s:boolean" use="required" />
          <s:attribute default="0" name="SubscriptionPingRate" type="s:int" />
        </s:complexType>
      </s:element>
      <s:complexType name="RequestOptions">
        <s:attribute default="true" name="ReturnErrorText" type="s:boolean" />
        <s:attribute default="false" name="ReturnDiagnosticInfo" type="s:boolean" />
        <s:attribute default="false" name="ReturnItemTime" type="s:boolean" />
        <s:attribute default="false" name="ReturnItemPath" type="s:boolean" />
        <s:attribute default="false" name="ReturnItemName" type="s:boolean" />
        <s:attribute name="RequestDeadline" type="s:dateTime" />
        <s:attribute name="ClientRequestHandle" type="s:string" />
        <s:attribute name="LocaleID" type="s:string" />
      </s:complexType>
      <s:complexType name="SubscribeRequestItemList">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="Items" type="tns:SubscribeRequestItem" />
        </s:sequence>
        <s:attribute name="ItemPath" type="s:string" />
        <s:attribute name="ReqType" type="s:QName" use="required" />
        <s:attribute name="Deadband" type="s:float" />
        <s:attribute name="RequestedSamplingRate" type="s:int" />
        <s:attribute name="EnableBuffering" type="s:boolean" />
      </s:complexType>
      <s:complexType name="SubscribeRequestItem">
        <s:attribute name="ItemPath" type="s:string" />
        <s:attribute name="ReqType" type="s:QName" use="required" />
        <s:attribute name="ItemName" type="s:string" />
        <s:attribute name="ClientItemHandle" type="s:string" />
        <s:attribute name="Deadband" type="s:float" />
        <s:attribute name="RequestedSamplingRate" type="s:int" />
        <s:attribute name="EnableBuffering" type="s:boolean" />
      </s:complexType>
      <s:complexType name="SubscribeReplyItemList">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="Items" type="tns:SubscribeItemValue" />
        </s:sequence>
        <s:attribute name="RevisedSamplingRate" type="s:int" />
      </s:complexType>
      <s:complexType name="SubscribeItemValue">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="1" name="ItemValue" type="tns:ItemValue" />
        </s:sequence>
        <s:attribute name="RevisedSamplingRate" type="s:int" />
      </s:complexType>
      <s:complexType name="ItemValue">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="1" name="DiagnosticInfo" type="s:string" />
          <s:element minOccurs="0" maxOccurs="1" name="Value" />
          <s:element minOccurs="0" maxOccurs="1" name="Quality" type="tns:OPCQuality" />
        </s:sequence>
        <s:attribute name="ValueTypeQualifier" type="s:QName" use="required" />
        <s:attribute name="ItemPath" type="s:string" />
        <s:attribute name="ItemName" type="s:string" />
        <s:attribute name="ClientItemHandle" type="s:string" />
        <s:attribute name="Timestamp" type="s:dateTime" />
        <s:attribute name="ResultID" type="s:QName" use="required" />
      </s:complexType>
      <s:complexType name="OPCQuality">
        <s:attribute default="good" name="QualityField" type="tns:qualityBits" />
        <s:attribute default="none" name="LimitField" type="tns:limitBits" />
        <s:attribute default="0" name="VendorField" type="s:unsignedByte" />
      </s:complexType>
      <s:simpleType name="qualityBits">
        <s:restriction base="s:string">
          <s:enumeration value="bad" />
          <s:enumeration value="badConfigurationError" />
          <s:enumeration value="badNotConnected" />
          <s:enumeration value="badDeviceFailure" />
          <s:enumeration value="badSensorFailure" />
          <s:enumeration value="badLastKnownValue" />
          <s:enumeration value="badCommFailure" />
          <s:enumeration value="badOutOfService" />
          <s:enumeration value="badWaitingForInitialData" />
          <s:enumeration value="uncertain" />
          <s:enumeration value="uncertainLastUsableValue" />
          <s:enumeration value="uncertainSensorNotAccurate" />
          <s:enumeration value="uncertainEUExceeded" />
          <s:enumeration value="uncertainSubNormal" />
          <s:enumeration value="good" />
          <s:enumeration value="goodLocalOverride" />
        </s:restriction>
      </s:simpleType>
      <s:simpleType name="limitBits">
        <s:restriction base="s:string">
          <s:enumeration value="none" />
          <s:enumeration value="low" />
          <s:enumeration value="high" />
          <s:enumeration value="constant" />
        </s:restriction>
      </s:simpleType>
      <s:element name="SubscribeResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="SubscribeResult" type="tns:ReplyBase" />
            <s:element minOccurs="0" maxOccurs="1" name="RItemList" type="tns:SubscribeReplyItemList" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="Errors" type="tns:OPCError" />
          </s:sequence>
          <s:attribute name="ServerSubHandle" type="s:string" />
        </s:complexType>
      </s:element>
      <s:element name="SubscriptionPolledRefresh">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="Options" type="tns:RequestOptions" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="ServerSubHandles" type="s:string" />
          </s:sequence>
          <s:attribute name="HoldTime" type="s:dateTime" />
          <s:attribute default="0" name="WaitTime" type="s:int" />
          <s:attribute default="false" name="ReturnAllItems" type="s:boolean" />
        </s:complexType>
      </s:element>
      <s:complexType name="SubscribePolledRefreshReplyItemList">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="Items" type="tns:ItemValue" />
        </s:sequence>
        <s:attribute name="SubscriptionHandle" type="s:string" />
      </s:complexType>
      <s:element name="SubscriptionPolledRefreshResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="SubscriptionPolledRefreshResult" type="tns:ReplyBase" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="InvalidServerSubHandles" type="s:string" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="RItemList" type="tns:SubscribePolledRefreshReplyItemList" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="Errors" type="tns:OPCError" />
          </s:sequence>
          <s:attribute default="false" name="DataBufferOverflow" type="s:boolean" />
        </s:complexType>
      </s:element>
      <s:element name="SubscriptionCancel">
        <s:complexType>
          <s:attribute name="ServerSubHandle" type="s:string" />
          <s:attribute name="ClientRequestHandle" type="s:string" />
        </s:complexType>
      </s:element>
      <s:element name="SubscriptionCancelResponse">
        <s:complexType>
          <s:attribute name="ClientRequestHandle" type="s:string" />
        </s:complexType>
      </s:element>
      <s:element name="GetStatus">
        <s:complexType>
          <s:attribute name="LocaleID" type="s:string" />
          <s:attribute name="ClientRequestHandle" type="s:string" />
        </s:complexType>
      </s:element>
      <s:complexType name="ServerStatus">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="1" name="StatusInfo" type="s:string" />
          <s:element minOccurs="0" maxOccurs="1" name="VendorInfo" type="s:string" />
          <s:element minOccurs="0" maxOccurs="unbounded" name="SupportedLocaleIDs" type="s:string" />
          <s:element minOccurs="0" maxOccurs="unbounded" name="SupportedInterfaceVersions" type="tns:interfaceVersion" />
        </s:sequence>
        <s:attribute name="StartTime" type="s:dateTime" use="required" />
        <s:attribute name="ProductVersion" type="s:string" />
      </s:complexType>
      <s:simpleType name="interfaceVersion">
        <s:restriction base="s:string">
          <s:enumeration value="XML_DA_Version_1_0" />
          <s:enumeration value="DX_Version_1_0" />
        </s:restriction>
      </s:simpleType>
      <s:element name="GetStatusResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="GetStatusResult" type="tns:ReplyBase" />
            <s:element minOccurs="0" maxOccurs="1" name="Status" type="tns:ServerStatus" />
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="Browse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="unbounded" name="PropertyNames" type="s:QName" />
          </s:sequence>
          <s:attribute name="LocaleID" type="s:string" />
          <s:attribute name="ClientRequestHandle" type="s:string" />
          <s:attribute name="ItemPath" type="s:string" />
          <s:attribute name="ItemName" type="s:string" />
          <s:attribute name="ContinuationPoint" type="s:string" />
          <s:attribute default="0" name="MaxElementsReturned" type="s:int" />
          <s:attribute default="all" name="BrowseFilter" type="tns:browseFilter" />
          <s:attribute name="ElementNameFilter" type="s:string" />
          <s:attribute name="VendorFilter" type="s:string" />
          <s:attribute default="false" name="ReturnAllProperties" type="s:boolean" />
          <s:attribute default="false" name="ReturnPropertyValues" type="s:boolean" />
          <s:attribute default="false" name="ReturnErrorText" type="s:boolean" />
        </s:complexType>
      </s:element>
      <s:simpleType name="browseFilter">
        <s:restriction base="s:string">
          <s:enumeration value="all" />
          <s:enumeration value="branch" />
          <s:enumeration value="item" />
        </s:restriction>
      </s:simpleType>
      <s:complexType name="BrowseElement">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="Properties" type="tns:ItemProperty" />
        </s:sequence>
        <s:attribute name="Name" type="s:string" />
        <s:attribute name="ItemPath" type="s:string" />
        <s:attribute name="ItemName" type="s:string" />
        <s:attribute name="IsItem" type="s:boolean" use="required" />
        <s:attribute name="HasChildren" type="s:boolean" use="required" />
      </s:complexType>
      <s:element name="BrowseResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="BrowseResult" type="tns:ReplyBase" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="Elements" type="tns:BrowseElement" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="Errors" type="tns:OPCError" />
          </s:sequence>
          <s:attribute name="ContinuationPoint" type="s:string" />
          <s:attribute default="false" name="MoreElements" type="s:boolean" />
        </s:complexType>
      </s:element>
      <s:element name="Read">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="Options" type="tns:RequestOptions" />
            <s:element minOccurs="0" maxOccurs="1" name="ItemList" type="tns:ReadRequestItemList" />
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:complexType name="ReadRequestItemList">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="Items" type="tns:ReadRequestItem" />
        </s:sequence>
        <s:attribute name="ItemPath" type="s:string" />
        <s:attribute name="ReqType" type="s:QName" use="required" />
        <s:attribute name="MaxAge" type="s:int" />
      </s:complexType>
      <s:complexType name="ReadRequestItem">
        <s:attribute name="ItemPath" type="s:string" />
        <s:attribute name="ReqType" type="s:QName" use="required" />
        <s:attribute name="ItemName" type="s:string" />
        <s:attribute name="ClientItemHandle" type="s:string" />
        <s:attribute name="MaxAge" type="s:int" />
      </s:complexType>
      <s:complexType name="ReplyItemList">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="Items" type="tns:ItemValue" />
        </s:sequence>
        <s:attribute name="Reserved" type="s:string" />
      </s:complexType>
      <s:element name="ReadResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="ReadResult" type="tns:ReplyBase" />
            <s:element minOccurs="0" maxOccurs="1" name="RItemList" type="tns:ReplyItemList" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="Errors" type="tns:OPCError" />
          </s:sequence>
        </s:complexType>
      </s:element>
      <s:element name="Write">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="Options" type="tns:RequestOptions" />
            <s:element minOccurs="0" maxOccurs="1" name="ItemList" type="tns:WriteRequestItemList" />
          </s:sequence>
          <s:attribute name="ReturnValuesOnReply" type="s:boolean" use="required" />
        </s:complexType>
      </s:element>
      <s:complexType name="WriteRequestItemList">
        <s:sequence>
          <s:element minOccurs="0" maxOccurs="unbounded" name="Items" type="tns:ItemValue" />
        </s:sequence>
        <s:attribute name="ItemPath" type="s:string" />
      </s:complexType>
      <s:element name="WriteResponse">
        <s:complexType>
          <s:sequence>
            <s:element minOccurs="0" maxOccurs="1" name="WriteResult" type="tns:ReplyBase" />
            <s:element minOccurs="0" maxOccurs="1" name="RItemList" type="tns:ReplyItemList" />
            <s:element minOccurs="0" maxOccurs="unbounded" name="Errors" type="tns:OPCError" />
          </s:sequence>
        </s:complexType>
      </s:element>
    </s:schema>
  </wsdl:types>
  <wsdl:message name="GetPropertiesSoapIn">
    <wsdl:part name="parameters" element="tns:GetProperties" />
  </wsdl:message>
  <wsdl:message name="GetPropertiesSoapOut">
    <wsdl:part name="parameters" element="tns:GetPropertiesResponse" />
  </wsdl:message>
  <wsdl:message name="SubscribeSoapIn">
    <wsdl:part name="parameters" element="tns:Subscribe" />
  </wsdl:message>
  <wsdl:message name="SubscribeSoapOut">
    <wsdl:part name="parameters" element="tns:SubscribeResponse" />
  </wsdl:message>
  <wsdl:message name="SubscriptionPolledRefreshSoapIn">
    <wsdl:part name="parameters" element="tns:SubscriptionPolledRefresh" />
  </wsdl:message>
  <wsdl:message name="SubscriptionPolledRefreshSoapOut">
    <wsdl:part name="parameters" element="tns:SubscriptionPolledRefreshResponse" />
  </wsdl:message>
  <wsdl:message name="SubscriptionCancelSoapIn">
    <wsdl:part name="parameters" element="tns:SubscriptionCancel" />
  </wsdl:message>
  <wsdl:message name="SubscriptionCancelSoapOut">
    <wsdl:part name="parameters" element="tns:SubscriptionCancelResponse" />
  </wsdl:message>
  <wsdl:message name="GetStatusSoapIn">
    <wsdl:part name="parameters" element="tns:GetStatus" />
  </wsdl:message>
  <wsdl:message name="GetStatusSoapOut">
    <wsdl:part name="parameters" element="tns:GetStatusResponse" />
  </wsdl:message>
  <wsdl:message name="BrowseSoapIn">
    <wsdl:part name="parameters" element="tns:Browse" />
  </wsdl:message>
  <wsdl:message name="BrowseSoapOut">
    <wsdl:part name="parameters" element="tns:BrowseResponse" />
  </wsdl:message>
  <wsdl:message name="ReadSoapIn">
    <wsdl:part name="parameters" element="tns:Read" />
  </wsdl:message>
  <wsdl:message name="ReadSoapOut">
    <wsdl:part name="parameters" element="tns:ReadResponse" />
  </wsdl:message>
  <wsdl:message name="WriteSoapIn">
    <wsdl:part name="parameters" element="tns:Write" />
  </wsdl:message>
  <wsdl:message name="WriteSoapOut">
    <wsdl:part name="parameters" element="tns:WriteResponse" />
  </wsdl:message>
  <wsdl:portType name="OpcXmlDaSrvSoap">
    <wsdl:operation name="GetProperties">
      <wsdl:input message="tns:GetPropertiesSoapIn" />
      <wsdl:output message="tns:GetPropertiesSoapOut" />
    </wsdl:operation>
    <wsdl:operation name="Subscribe">
      <wsdl:input message="tns:SubscribeSoapIn" />
      <wsdl:output message="tns:SubscribeSoapOut" />
    </wsdl:operation>
    <wsdl:operation name="SubscriptionPolledRefresh">
      <wsdl:input message="tns:SubscriptionPolledRefreshSoapIn" />
      <wsdl:output message="tns:SubscriptionPolledRefreshSoapOut" />
    </wsdl:operation>
    <wsdl:operation name="SubscriptionCancel">
      <wsdl:input message="tns:SubscriptionCancelSoapIn" />
      <wsdl:output message="tns:SubscriptionCancelSoapOut" />
    </wsdl:operation>
    <wsdl:operation name="GetStatus">
      <wsdl:input message="tns:GetStatusSoapIn" />
      <wsdl:output message="tns:GetStatusSoapOut" />
    </wsdl:operation>
    <wsdl:operation name="Browse">
      <wsdl:input message="tns:BrowseSoapIn" />
      <wsdl:output message="tns:BrowseSoapOut" />
    </wsdl:operation>
    <wsdl:operation name="Read">
      <wsdl:input message="tns:ReadSoapIn" />
      <wsdl:output message="tns:ReadSoapOut" />
    </wsdl:operation>
    <wsdl:operation name="Write">
      <wsdl:input message="tns:WriteSoapIn" />
      <wsdl:output message="tns:WriteSoapOut" />
    </wsdl:operation>
  </wsdl:portType>
  <wsdl:binding name="OpcXmlDaSrvSoap" type="tns:OpcXmlDaSrvSoap">
    <soap:binding transport="http://schemas.xmlsoap.org/soap/http" style="document" />
    <wsdl:operation name="GetProperties">
      <soap:operation soapAction="http://opcfoundation.org/webservices/XMLDA/1.0/GetProperties" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="Subscribe">
      <soap:operation soapAction="http://opcfoundation.org/webservices/XMLDA/1.0/Subscribe" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="SubscriptionPolledRefresh">
      <soap:operation soapAction="http://opcfoundation.org/webservices/XMLDA/1.0/SubscriptionPolledRefresh" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="SubscriptionCancel">
      <soap:operation soapAction="http://opcfoundation.org/webservices/XMLDA/1.0/SubscriptionCancel" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="GetStatus">
      <soap:operation soapAction="http://opcfoundation.org/webservices/XMLDA/1.0/GetStatus" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="Browse">
      <soap:operation soapAction="http://opcfoundation.org/webservices/XMLDA/1.0/Browse" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="Read">
      <soap:operation soapAction="http://opcfoundation.org/webservices/XMLDA/1.0/Read" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
    <wsdl:operation name="Write">
      <soap:operation soapAction="http://opcfoundation.org/webservices/XMLDA/1.0/Write" style="document" />
      <wsdl:input>
        <soap:body use="literal" />
      </wsdl:input>
      <wsdl:output>
        <soap:body use="literal" />
      </wsdl:output>
    </wsdl:operation>
  </wsdl:binding>
  <wsdl:service name="OpcXmlDaSrv">
    <documentation xmlns="http://schemas.xmlsoap.org/wsdl/" />
    <wsdl:port name="OpcXmlDaSrvSoap" binding="tns:OpcXmlDaSrvSoap">
      <soap:address location="" />
    </wsdl:port>
  </wsdl:service>
</wsdl:definitions>
