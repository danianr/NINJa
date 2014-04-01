from socket import *
from datetime import *
from subprocess import *
from collections import deque
import os
import time


class IndexView(object):

   def __init__(self, username, indexFunc, displayFunc):
       self.username = username
       self.timestamp = time.time()
       self.indexFunc = indexFunc
       self.displayFunc = displayFunc
       self.internal  = self.indexFunc(username)
       self.refreshReq = deque()
       self.dirty = False
       self.delay = 120

   def refresh(self, event=None):
       now = time.time()
       self.refreshReq.append(now)
       for req in self.refreshReq:
          if (req + self.delay) < now or self.dirty:
             break
       else:
          return

       self.internal = self.indexFunc(username)
       self.timestamp = now
       self.refreshReq.clear()

   def isDirty(self):
       return self.dirty

   def setDirty(self):
       self.dirty = True

   def map(self, iterable):
       return map(lambda i: self.internal[int(i)], iterable)


   # Only define getter accessors since this is technically
   # a read-only snapshot
   def __getitem__(self, x):
       return self.internal[x]

   def __getslice__(self, x, y):
       return self.internal[x:y]

   def __len__(self):
       return len(self.internal)

   def __iter__(self):
       return iter(map(self.displayFunc,  self.internal))



class CloudAdapter(object):

   def __init__(self, path):
       self.controlpath = path
       self.sftp = '/usr/bin/sftp'
       self.landing = '/tmp'
       self.remote_path = '/spare/remote'
       if not os.path.exists(self.controlpath):
          e = OSError()
          e.errno=2
          e.strerror='No such file or directory'
          e.filename=path
          raise e


   def _getfile(self, cmd):
       s = socket(AF_UNIX, SOCK_STREAM, 0)
       s.connect(self.controlpath)
       s.sendall(cmd)
       return s.makefile()


   def _retrieve(self, node, username, sha512):
       command_script = 'cd %s/%s\nget %s\nexit\n' % (self.remote_path, username, sha512)
       return self._sftp_wrapper(self, node, command_script)


   def _store(self, node, username, sha512, file):
       command_script = 'mkdir %s/%s\ncd %s/%s\nput %s %s\nexit\n' % (self.remote_path,
                                         username, self.remote_path, username, file, sha512)
       return self._sftp_wrapper(self, node, command_script)


   def _sftp_wrapper(self, node, command_script):
       p = Popen( [self.sftp, '-b-', node], shell=False, bufsize=1024, cwd=self.landing)
       p.communicate(command_script)
       maxtime = time() + 36
       while ( time() < maxtime ):
          retstatus = p.poll()
          if retstatus == 0:
             return True
          elif retstatus is None:
             time.sleep(2) 
          else:
             return False
       p.kill()
       return False
 

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
           if printer is not None and printer != '0.0.0.0':
              try:
                  print 'attempting for printer gethostbyaddr(%s)' % (printer,)
                  (printer, aliases, ip_list) = gethostbyaddr(printer)
              except:
                  printer = 'UNKNOWN'
           else:
              printer = 'UNKNOWN'

           if ipaddr is not None and ipaddr != '0.0.0.0':
              try:
                  print 'attempting for client gethostbyaddr(%s)' % (ipaddr,)
                  (client, aliases, ip_list)  = gethostbyaddr(ipaddr)
              except:
                  client = 'unknown'
           else:
              print 'using localhost for client'
              client = 'localhost'
           index.append((uuid, sha512, created, sheets, duplex, client, printer, username, title))
       return index 


   def indexStr(self, tuple):
        (uuid, sha512, created, sheets, duplex, client, printer, username, title) = tuple
        return '%s  %s  %d   %s' % ( client, created.strftime('%a %I:%M:%S %p'), sheets, title[:32])


   def retrieveJob(self, username, sha512, gridlist=None):
        userrand = random.Random(username)

        if gridlist is not None:
           nodes = userrand(gridlist, 3)
        else:
           nodes = ('localhost',)

        for node in nodes:
           if self._retrieve(node, username, sha512):
              print 'job %s/%s successfully retrieved from %s\n' % (username, sha512, node)
              return '%s/%s' % (self.landing, sha512)
        return None
        

   def storeJob(self, job, gridlist=None):
        username = job.username
        sha512   = job.sha512
        userrand = random.Random(username)

        if gridlist is not None:
           nodes = userrand(gridlist, 3)
        else:
           nodes = ('localhost',)

        for node in nodes:
           if self._store(node, username, sha512):
              print 'job %s/%s successfully stored to %s\n' % (username, sha512, node)
           else:
              print 'problem storing %s/%s to %s\n' % (username, sha512, node)
