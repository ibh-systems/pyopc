#!/usr/bin/env python2.4

''' XMLDA to ESD proxy '''
from PyOPC.servers import esdsrv

from twisted.application import service, internet
from twisted.internet import reactor
from twisted.web import resource, server

from esdsim_server import *

class ESDSimService(internet.TCPServer):
    def __init__(self):
        internet.TCPServer.__init__(self,ESDSIM_PORT, ESDFactory(ESDSim()))

application = service.Application("OPC")

# Start the basic server
xdasrv = esdsrv.ESDProxy(http_log_fn = 'http.log')
#xdasrv = esdsrv.ESDProxy(http_log_fn = '', esd_host = 'violin.qwer.tk', esd_port = 1111)
root = resource.Resource()
root.putChild('',xdasrv)
webService = internet.TCPServer(8000,server.Site(root))
webService.setName("OPC XMLDA")
webService.setServiceParent(application)
        
esdService = ESDSimService()
esdService.setServiceParent(application)

                                    
