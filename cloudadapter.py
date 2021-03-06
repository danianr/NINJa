from socket import *
from datetime import *
from subprocess import Popen, PIPE
from collections import deque
import sys
import os
import time
import random
import copy

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

       self.internal = self.indexFunc(self.username)
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

   def __init__(self, path, maxsize=2147483647):
       self.controlpath = path
       self.sftp = '/usr/bin/sftp'
       self.landing = '/svc/landing'
       self.remote_path = '/svc/remote'
       self.maxsize = maxsize
       if not os.path.exists(self.controlpath):
          e = OSError()
          e.errno=2
          e.strerror='No such file or directory'
          e.filename=path
          raise e



   def _topoCalc(self, gridlist):
       print >> sys.stderr, time.time(), "Entrance into CloudAdapter._topoCalc(", repr(gridlist), ")" 
       remaining = copy.copy(gridlist)
       topolist = []
       thishost = getfqdn()
       if thishost in remaining:
          remaining.remove(thishost)
          topolist.append(thishost)
       
       for timeoutval in [ 0.000260, 0.000650, 0.002000 ]:
          for node in remaining:
             s = socket()
             s.settimeout(timeoutval)
             iaddr = ( gethostbyname(node), 22 )
             try: 
                s.connect(iaddr)
                s.close()
                topolist.append(node)
                remaining.remove(node)
             except timeout:
                print >> sys.stderr, time.time(), 'Unable to connect to node %s within %fs\n' % (node, timeoutval)
       topolist.extend(remaining)
       print >> sys.stderr, time.time(), "Return from CloudAdapter._topoCalc => ", repr(topolist)
       return topolist

                
   def _getfile(self, cmd):
       s = socket(AF_UNIX, SOCK_STREAM, 0)
       s.connect(self.controlpath)
       s.sendall(cmd)
       return s.makefile()


   def _retrieve(self, node, username, sha512):
       command_script = 'cd %s/%s\nget %s\nexit\n' % (self.remote_path, username, sha512)
       return self._sftp_wrapper(node, command_script)


   def _store(self, node, username, sha512, file):
       command_script = 'mkdir %s/%s\ncd %s/%s\nput %s %s\nexit\n' % (self.remote_path,
                                         username, self.remote_path, username, file, sha512)
       return self._sftp_wrapper(node, command_script)


   def _sftp_wrapper(self, node, command_script):
       print >> sys.stderr, time.time(), '_sftp_wrapper(%s, %s, %s)' % (self, node, command_script)
       p = Popen( [self.sftp, node], stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=False, bufsize=1024, cwd=self.landing)
       p.communicate(command_script)
       maxtime = time.time() + 36
       while ( time.time() < maxtime ):
          retstatus = p.poll()
          print >> sys.stderr, time.time(), "_sftp_wrapper.retstatus = ", retstatus
          if retstatus == 0:
             return True
          elif retstatus is None:
             time.sleep(2) 
          else:
             return False
       p.kill()
       return False


   def registerGridList(self, gridlist):
       self.topolist = self._topoCalc(gridlist)
       self.gridlist = gridlist 


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
           else:
              duplex = True
           sheets = pageinfo >> 1
           if printer is not None and printer != '0.0.0.0':
              try:
                  (printer, aliases, ip_list) = gethostbyaddr(printer)
              except:
                  printer = 'UNKNOWN'
           else:
              printer = 'UNKNOWN'

           if ipaddr is not None and ipaddr != '0.0.0.0':
              try:
                  (client, aliases, ip_list)  = gethostbyaddr(ipaddr)
              except:
                  client = 'unknown'
           else:
              client = 'localhost'
           index.append((uuid, sha512, created, sheets, duplex, client, printer, username, title))
       return index 


   def indexStr(self, tuple):
        (uuid, sha512, created, sheets, duplex, client, printer, username, title) = tuple
        expiretime = created + timedelta(0, 14400)  # four hours from time created
        return '%-32s  %-12s  %6s  %15s' % (title[:32], printer.partition('-')[0], sheets, expiretime.strftime('%a %I:%M:%S %p'))


   def retrieveJob(self, username, sha512, gridlist=None):
        userrand = random.Random()
        userrand.seed(username)

        # Can't reference a member of an argument as a default value
        if gridlist is None:
           gridlist = self.gridlist

        if gridlist is not None:
           try:
                nodes = userrand.sample(gridlist, 3)
                nodes = filter(lambda h: h in nodes, self.topolist)
           except ValueError:
                nodes = gridlist[0:3]
        else:
           nodes = ('localhost',)

        for node in nodes:
           print >> sys.stderr, 'retreiveJob trying node: ', node
           if self._retrieve(node, username, sha512):
              print >> sys.stderr, time.time(), 'job %s/%s successfully retrieved from %s\n' % (username, sha512, node)
              localfile = self.landing + os.sep + sha512
              if os.path.exists(localfile):
                 return localfile
              else:
                 print >> sys.stderr, time.time(), "unable to locate ", localfile
           else:
              print >> sys.stderr, time.time(), 'unable to retreive job %s/%s from node %s\n' % (username, sha512, node)
              self.topolist.remove(node)
              self.topolist.append(node)
        return None
        

   def storeJob(self, job, gridlist=None):
        if job.size > self.maxsize:
           print >> sys.stderr, time.time(), 'Not attempting to store job:%d size (%d bytes) is larger than allowed\n' % (job.jobId, job.size)
           job.removeTmpFile()
           return
        username = job.username
        sha512   = job.sha512
        tmpfile  = job.tmpfile
        userrand = random.Random()
        userrand.seed(username)

        # Can't reference a member of an argument as a default value
        if gridlist is None:
           gridlist = self.gridlist

        if gridlist is not None:
        
           try:
                nodes = userrand.sample(gridlist, 3)
           except ValueError:
                nodes = gridlist[0:3]
           pid = Popen(["/home/dcedev/ninja/sftp_push.sh", username, tmpfile, sha512, nodes[0], nodes[1], nodes[2]]).pid
           print >> sys.stderr, time.time(), repr(["/home/dcedev/ninja/sftp_push.sh", username, tmpfile, sha512, nodes[0], nodes[1], nodes[2]]), pid
        else:
           nodes = ('localhost',)

