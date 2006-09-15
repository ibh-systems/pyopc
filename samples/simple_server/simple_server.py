#!/usr/bin/env python2.4

from twisted.internet import reactor,defer
from PyOPC.servers.basic import BasicXDAServer

# Read sample OPC items for testing
import sample_items

class SimpleXDAServer(BasicXDAServer):
    OPCItems = sample_items.TestOPCItems
    Ignore_ReturnItemPath=True
    Ignore_ReturnItemName=True

if __name__ == '__main__':
    # Start the basic server
    from twisted.web import resource, server
    xdasrv = SimpleXDAServer(http_log_fn = 'http.log')
    root = resource.Resource()
    root.putChild('',xdasrv)
    site = server.Site(root)
    reactor.listenTCP(8000, site)
    reactor.run()
