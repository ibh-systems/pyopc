''' Sample OPC Items for testing purposes '''

import datetime
from PyOPC.OPCContainers import *

# Initial timestamp for all ItemValues
def_ts = datetime.datetime(2006, 2, 15, 12, 15, 18)

TestOPCItems = ((ItemContainer(ItemName='sample_integer',
                               Value=14,
                               Timestamp=def_ts,
                               QualityField='good',
                               LimitField='none',
                               VendorField=0),
                 (OPCProperty(Name='accessRights',
                              Value='readWriteable'),
                  OPCProperty(Name='description',
                              Value='Integer Item'),
                  OPCProperty(Name='MyProperty',
                              Value = 'foobar',
                              ItemPath='MyPath',
                              ItemName='MyName'))),
                (ItemContainer(ItemName='sample_float',
                               Value=96.43,
                               Timestamp=def_ts,
                               QualityField='good',
                               LimitField='none',
                               VendorField=0),
                 (OPCProperty(Name='accessRights',
                              Value='readWriteable'),)))
