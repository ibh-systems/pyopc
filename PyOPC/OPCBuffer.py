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
# A buffer for OPC XML-DA servers
# The buffer has a fixed size after creation
# It has to store Items with values
# When the buffer is full, the oldest entries are tossed
# When an entry is tossed, it has to be recorded
# A read-function should retrieve all values for an item
# When an item is read, it should be expunged from the buffer
# 

from collections import deque

class OPCBuffer(object):
    ''' Buffer with a Deque '''

    def __init__(self,maxsize):
        self.maxsize = maxsize
        # Dictionary that records lost items
        self.LostValues = set()
        self._buffer = deque()

    def store(self,key,value):
        ''' Store a value in the buffer '''
        buf = self._buffer
        buf.appendleft((key,value))
        if len(buf) > self.maxsize:
            self.LostValues.add(buf.pop()[0])

    def islost(self,key,reset = False):
        ''' Report if some values for a key were lost '''
        isthere = key in self.LostValues
        if reset and isthere: self.LostValues.remove(key)
        return isthere

    def retrieve(self,key):
        ''' Retrieve all values for a key from the buffer '''
        # List of values, the oldest values come first
        buf = self._buffer
        pop = buf.pop
        buf_rotate = buf.rotate
        values = []
        values_append = values.append
        for cnt in xrange(len(buf)):
            if buf[-1][0] == key:
                values_append(pop()[-1])
            else:
                buf_rotate()
        return self.islost(key,reset=True), values
        

if __name__ == '__main__':
    import time
    b = OPCBuffer(10)
    # store some items
    for i in range(1,5):
        b.store('Item1',i)
    for i in range(1,5):
        b.store('Item2',i)
    for i in range(1,5):
        b.store('Item3',i)
    # Retrieve these items
    print b._buffer
    print b.retrieve('Item1')
    print b.retrieve('Item2')
    print b.retrieve('Item3')
    print b.retrieve('asdf')
    print b._buffer

    # push out an item completely
    print "Islost Test"
    b = OPCBuffer(10)
    for i in range(1,5):
        b.store('Item1',i)
    for i in range(1,12):
        b.store('Item2',i)
    print b.retrieve('Item1')
    print b.retrieve('Item2')

    # Now make a HUGE Buffer
    print "Huge Buffer Test"
    b = OPCBuffer(300000)
    t = time.time()
    for i in xrange(1,150000):
        b.store('Item1',i)
    for i in xrange(1,10):
        b.store('Item2',i)
    for i in xrange(1,150000):
        b.store('Item3',i)
    print b.islost('Item1')
    print 'Storing all items took: %s' % str(time.time()-t)
    t = time.time()
    print b.retrieve('Item2')
    print 'Retrieving the items took: %s' % str(time.time()-t)
    
