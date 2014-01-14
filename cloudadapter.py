from socket import *
from datetime import *


class CloudAdapter(object):

   def __init__(self, path):
       self.controlpath = path


   def _getfile(self, cmd):
       s = socket(AF_UNIX, SOCK_STREAM, 0)
       s.connect(self.controlpath)
       s.sendall(cmd)
       return s.makefile()

   def getRawHeaders(self, username):
       cmd = 'return %s' % (username,)
       sock = self._getfile(cmd)
       rawheaders = sock.readlines()
       sock.close()
       return rawheaders

   def getHeaders(self, username):
       displayHeaders = []
       for raw in self.getRawHeaders(username):
           (uuid, sha512, created, pageinfo, ipaddr,
            printer, username, title ) = raw.split(':', 8)
           created = datetime.fromtimestamp(int(created))
           
           print 'ip:%s printer:%s user:%s' % (ipaddr, printer, username)
           #hs = ntohs(int(ipaddr))
           #print '%s n:%d  h:%d'  % (inet_ntoa(hs), ipaddr, hs)
           pageinfo = int(pageinfo)
           if (pageinfo % 2 == 0):
              duplex = False
              sheets = pageinfo >> 1
           elif ((pageinfo >> 1) % 2 == 0):
              duplex = True
              sheets = pageinfo >> 2
           else:
              duplex = True
              sheets = (pageinfo + 1 ) >> 2
           client = 'foo'
           header = '%s  %s  %d   %s' % ( client, created.strftime('%a %I:%M:%S %p'), sheets, title[:32])
           displayHeaders.append(header)
       return displayHeaders

if __name__ == '__main__':

   cloud = CloudAdapter('/tmp/keepersock')
   print cloud.getHeaders('dr2481')
