#!/usr/bin/env python2.4
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
