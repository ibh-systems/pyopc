#!/usr/bin/env python2.4

import random
from twisted.internet import reactor,defer
from PyOPC.servers.basic import BasicXDAServer

# Read sample OPC items for testing
import sample_items

class MyXDAServer(BasicXDAServer):
    OPCItems = sample_items.TestOPCItems
    StatusInfo = 'My Basic OPC XML-DA Server'

    def GetStatus(self, (IPH,inOptions,outOptions)):
        ''' Custom GetStatus that alters the Product Version'''

        outOptions['ProductVersion'] = str(random.choice(range(1,10)))
        
        return super(MyXDAServer, self).GetStatus((IPH,inOptions,outOptions))
        
if __name__ == '__main__':
    # Start the basic server
    from twisted.web import resource, server
    xdasrv = MyXDAServer(http_log_fn = 'http.log')
    root = resource.Resource()
    root.putChild('',xdasrv)
    site = server.Site(root)
    reactor.listenTCP(8000, site)
    reactor.run()
