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

   def getHeaders(self, username):
       cmd = 'return %s' % (username,)
       sock = self._getfile(cmd)
       rawheaders = sock.readlines()
       sock.close()
       return rawheaders

   def getIndex(self, username):
       index = []
       for raw in self.getHeaders(username):
           (uuid, sha512, created, pageinfo, ipaddr,
            printer, username, title ) = raw.split('\034', 8)
           created = datetime.fromtimestamp(int(created))
           
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
           try:
              (printer, aliases, ip_list) = gethostbyaddr(printer)
           except:
              printer = 'UNKOWN'

           try:
              (client, aliases, ip_list)  = gethostbyaddr(ipaddr)
           except:
              client = 'unknown'
           displaystr = '%s  %s  %d   %s' % ( client, created.strftime('%a %I:%M:%S %p'), sheets, title[:32])
           print '(%s, %s, %s, %s)\n' % (uuid, sha512, printer, displaystr) 
           index.append((uuid, sha512, printer, displaystr))
       return index 
