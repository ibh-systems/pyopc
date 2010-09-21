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
