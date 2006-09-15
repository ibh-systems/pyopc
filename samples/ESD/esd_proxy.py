#!/usr/bin/env python2.4

''' XMLDA to ESD proxy '''
from PyOPC.servers import esdsrv

if __name__ == '__main__':
    # Start the basic server
    from twisted.internet import reactor, task
    from twisted.web import resource, server
    xdasrv = esdsrv.ESDProxy(http_log_fn = 'http.log')
    #xdasrv = esdsrv.ESDProxy(http_log_fn = '', esd_host = 'violin.qwer.tk', esd_port = 1111)
    root = resource.Resource()
    root.putChild('',xdasrv)
    site = server.Site(root)
    reactor.listenTCP(8000, site)
    reactor.run()
