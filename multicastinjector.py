import unittest
import socket
import struct
import os
import re
import time
from multicast import MulticastMember
from mockjob import MockJob
from mockjob import MockQueue as JobQueue




unipattern =  re.compile('(?!.{9})([a-z]{2,7}[0-9]{1,6})')
address = '233.0.14.56'
port    = 34426
ttl     = 7
# Production uses port 34426, use port 34425 for unittesting
# so as not to interfere
mcast = MulticastMember(address, port, ttl , unipattern)

# use current time to generate valid jobs which won't be eliminated due to expiry
basetime = int(time.time())
testJobs = []
testJobs.append(MockJob(199, 'urn:uuid:18ba3287-4b3b-3425-77c3-8d2fea25bffd',
                'cd93b7ccec58480bb7d8089408066bda3a4048f8038811b072cc9acc9eb56edd0e34f51175bc437584abb0e17120524f6d04645ebfaeaa125bb0c249b1899e69', 'gsg8', basetime - 3000, 1, 'localhost', 'keeper.pl', False, 3))

testJobs.append(MockJob(211, 'urn:uuid:dd314744-71b4-390f-6684-06ac6ad4f2f4',
                '52d6138a377110d6e85be45405a9f1f1a4210f8a6ba0b70c58aa38a6f762ac92df86eb40e70cd9c5cf33af6209bd1fd845acbf7aeb60d1af6367d4a202566aec', 'dr2481', basetime - 1800, 7, 'localhost', '06_Green 2010_Calling all frequent flyers (newnew).ps', False, 3))

testJobs.append(MockJob(212, 'urn:uuid:a77de22c-5ea1-30aa-5275-272e27b0b61d',
                '072cd87025ca59d77b83736f0943a2ebcdf894444da24e27791977ad6d8d4b51e42d4c1c76b987b91a40792c4030a39b6b7540dde62a22f25d0a9f9863426efe', 'dr2481', basetime - 1100, 1, 'localhost', 'Inbox (427) - dr2481@columbia.edu - LionMail Mail', False, 3))

testJobs.append(MockJob(213, 'urn:uuid:477589bb-9a35-3fab-61b0-a89311e07c5b',
                'cd93b7ccec58480bb7d8089408066bda3a4048f8038811b072cc9acc9eb56edd0e34f51175bc437584abb0e17120524f6d04645ebfaeaa125bb0c249b1899e69', 'foobar', basetime - 1110, 1, 'localhost', 'keeper.pl', False, 3))

testJobs.append(MockJob(215, 'urn:uuid:b7fa6482-3ff5-3043-547d-2007c36b2391',
                'd3415520c533b510a4243fb4c56412fb371ff16f1c7cc26dec6007a7b475cd07c45ade1476e49c9f0d6e05c0b8c0079d764a0f28328d5c8e1f47b7a0ab1301f7', 'dr2481', basetime - 900, 2, 'localhost', 'Microsoft.com - Careers', False, 3))

testJobs.append(MockJob(217, 'urn:uuid:23e2529d-5a81-35a2-5b35-59e47825057c',
                'b9b8004ec67c11578a6eb3a3a821e7e8c0ed7ca28907a56d74bbbd4d691343dcbd34e2652447b83f59cdfe4c5bf130bff5595faeb5da0f8b554faa48b4fc65d0', 'dr2481', basetime - 600, 1, 'localhost', 'Inbox (507) - dr2481@columbia.edu - LionMail Mail', False, 3))

testJobs.append(MockJob(218, 'urn:uuid:d2b4e7a0-4a43-3509-51b8-5ad94a6c8c76',
                '217af37f15ffd8ca2a3692fbf2083c66b9438018620662a324fbbd5c8369850bef46b3e92dcf1c489134dc4071d9a4776ab4c424896d22ca8367845506336f4d', 'dr2481', basetime - 7, 6, 'localhost', '8.3. struct ? Interpret strings as packed binary data ? Python v2.6.5c2 documentation', False, 3))

testJobs.append(MockJob(219, 'urn:uuid:75ede9c2-6b5a-3f1b-4657-6e9a2ae6da79',
                '5be9c23961ebf72ae7df1047e31e74258ad6880cfc977e49a652a924515f5e39c9342f3ffcdc784fadadf787216924a0df69b2ea07974d87c70273d1f714a861', 'dr2481', basetime - 4, 4, 'localhost', 'Lesson: Notifications (The Java? Tutorials > Java Management Extensions (JMX))', False, 3))

testJobs.append(MockJob(223, 'urn:uuid:d7a80a3e-ef57-326d-5888-52a5c5d10d30',
                'de6894473b062b9ac7ef06016d350014c1b6b300fb916edd1121e6f8dfc310aa18e832a92d144390f96427424cda33ecc2af36ccdcf87b0353f57296d61f3364', 'dr2481', basetime, 1, 'localhost', 'New University Policy on Mail and Personal Safety - dr2481@columbia.edu - LionMail Mail', False, 3))


for job in testJobs:
    if unipattern.match(job.username):
       mcast.advertise(job)





