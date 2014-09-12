from Tkinter import *
import os
import posix
from joblist import JobList
import cups
import re
from collections import deque
import time
import sys


class Job(object):
   def __init__(self, conn=None, jobId=None, maxsize=2147483647):
       print >> sys.stderr, time.time(), 'Entry into Job(jobId=%s)' % (jobId,)
       self.jobId = jobId
       self.authenticated = False
       printerUri = conn.getJobAttributes(jobId).get('printer-uri')

       # This will raise an IPPError if the job has not finished transferring
       # in the form of IPPError: (1030, 'client-error-not-found')
       doc = conn.getDocument(printerUri, jobId, 1)
       print >> sys.stderr, time.time(), 'After getDocument() for jobId:', jobId
       self.size     = os.stat(doc['file']).st_size
       if self.size > maxsize:
          print >> sys.stderr, time.time(), 'Document size is larger than accepted:', self.size
          os.remove(doc['file'])
          self.error = 'Document PostScript is too large to be printed;\ntry printing from a Mac'
          self.pages = 0
          self.sha512 = 'NA'
       else:   

          # Note that the getDocument command must be issued prior to requesting
          # detailed job attributes such as document-format, job-originating-host-name
          # and job-originating-user-name, otherwise these attributes will be blank
          digest_cmd = '/usr/bin/nice /usr/bin/openssl dgst -sha512 %s' % ( doc['file'] )
          pagecount_cmd = './pagecount.sh %s %s' % ( doc['document-format'], doc['file'] )
          sha512 = os.popen(digest_cmd).read()
          print >> sys.stderr, time.time(), 'After the digest for jobId:', jobId
          pagecount = os.popen(pagecount_cmd).read()
          print >> sys.stderr, time.time(), 'After the pagecount for jobId:', jobId
          try:
              self.pages = int(pagecount)
              self.error    = None
          except ValueError:
              self.pages = 1
              self.error = 'Unable to determine pagecount, you will be charged for actual usage'
          self.sha512 = sha512[-129:-1]

       self.docFormat = doc['document-format']
       attr = conn.getJobAttributes(jobId)
       self.uuid = attr['job-uuid']
       self.creation = attr['time-at-creation']
       self.username = attr['job-originating-user-name'].encode('ascii','ignore')
       self.hostname = attr['job-originating-host-name'].encode('ascii','ignore')
       self.title = attr['job-name'].encode('ascii','replace')
       self.displayTitle = self.title[:47]
       self.jobState = attr['job-state']
       self.remote   = printerUri.endswith('/remote')

       # There is no need to keep the tmpfile around for remote jobs
       if self.remote and doc['file'] != "":
          os.remove(doc['file'])
          self.tmpfile = None
       elif self.size > maxsize:
          self.tmpfile = None
       else:
          self.tmpfile  = doc['file']
       

       if ( attr.has_key('Duplex')  and attr['Duplex'] != u'None' ):
           self.duplex = True
	   self.pages = ( self.pages % 2  + self.pages ) / 2
       else:
           self.duplex = False

       # Use the initially supplied jobId for the returned hash value
       # defined using a lambda with a closure to make value immutable
       self.__hash__ = lambda : jobId


   def __cmp__(self, other):
       if self.creation < other.creation:
          return -1
       elif self.creation > other.creation:
          return 1
       else:
          return 0

   def __repr__(self):
       return '<jobId: %d, uuid: \'%s\', creation: %d, username: \'%s\', hostname: \'%s\', title:\'%s\', pages: %d, jobState: %d, duplex: %s>' \
                     % ( self.jobId, self.uuid, self.creation, self.username, self.hostname, self.title, self.pages, self.jobState, self.duplex )

   def __str__(self):
       return '%4d  %-12s %-18s %-48s  %6s' % ( self.jobId,  self.username, self.hostname[:18], self.displayTitle[:48], self.pages )

   def removeTmpFile(self):
       if self.tmpfile is not None and self.tmpfile != "":
          os.remove(self.tmpfile)


class JobMapping(object):
   # Takes a sequence of Job objects, produces an iterator
   # suitable for supplying to a a listbox (textual description)
   # and allows direct access to Job objects based on their
   # position.  Also takes a list of positions and returns
   # a tuple of Job objects associated with each

   def __init__(self, iterable, username):
       self.timestamp = time.time()
       self.internal = list()
       self.internal.extend(iterable)
       self.username = username
       self.dirty = False

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
       return iter(map(lambda j: j.__str__(), self.internal))


class JobQueue(object):
   def __init__(self, unipattern, conn, multicastHandler=None, cloudAdapter=None, maxsize=2147483647):
       self.unipattern = unipattern
       self.conn       = conn
       self.mcast      = multicastHandler
       self.cloud      = cloudAdapter
       self.jobs       = dict()
       self.claimed    = dict()
       self.unclaimed  = deque()
       self.refreshReq = deque()
       self.claimedMapFrame   = None
       self.unclaimedMapFrame = None
       self.delay      = 23	# seconds
       self.maxsize    = maxsize
       self.processing = None


   def getMapping(self, username=None):
       self.refresh()
       if username is None:
          if self.unclaimedMapFrame is None or \
             self.unclaimedMapFrame.isDirty():
               self.unclaimedMapFrame = JobMapping(self.unclaimed, None)
          return self.unclaimedMapFrame
       else:
          if self.claimedMapFrame is None or   \
             self.claimedMapFrame.isDirty() or \
             self.claimedMapFrame.username != username:
               if self.claimed.has_key(username):
                  self.claimedMapFrame = JobMapping(self.claimed[username], username)
               else:
                  self.claimedMapFrame = JobMapping([], username)
          return self.claimedMapFrame
            

   def refresh(self, event=None, interjobHook=None, force=False):
       if self.processing is not None:
          return
       now = time.time()
       self.refreshReq.append(now)
       for req in self.refreshReq:
          if force or (req + self.delay) < now:
             self.processing = now
             break
       else:
          return
       incompleteJobs = self.conn.getJobs(which_jobs='not-completed')
       self.remove( filter( lambda x: not incompleteJobs.has_key(x), self.jobs.keys()) )
       for jobId in filter( lambda x: not self.jobs.has_key(x), incompleteJobs.keys()):
          try:
             j = Job(self.conn, jobId, self.maxsize)
             if not j.remote:
                self.add(j)
          except cups.IPPError as e:
             print("caught an IPPError",e)
             continue
          if interjobHook is not None:
             interjobHook()
       self.refreshReq.clear()
       rettime = time.time()
       print >> sys.stderr, rettime, 'Total elapsed time for jobqueue.refresh():', rettime - now
       self.processing = None

   def add(self, job):
       # updates the main index
       self.jobs[job.jobId] = job
       if self.unipattern.match(job.username):
          if job.username not in self.claimed:
             self.claimed[job.username] = deque()
          self.claimed[job.username].appendleft(job)
          if self.claimedMapFrame is not None and \
             self.claimedMapFrame.username == job.username:
                self.claimedMapFrame.setDirty()
          if self.cloud is not None and self.mcast is not None and job.size <= self.cloud.maxsize:
             self.mcast.advertise(job)
             self.cloud.storeJob(job)
       else:
          self.unclaimed.appendleft(job)
          if self.unclaimedMapFrame is not None:
             self.unclaimedMapFrame.setDirty()


   def remove(self, removedJobs):
       for id in filter( lambda x: self.jobs.has_key(x), removedJobs):
           j = self.jobs[id]
           if j in self.unclaimed:
              self.unclaimed.remove(j)
              if self.unclaimedMapFrame is not None:
                 self.unclaimedMapFrame.setDirty()
           else:
              username=j.username
              if self.claimed.has_key(username):
                 self.claimed[username].remove(j)
                 if ( len(self.claimed[username]) == 0 ):
                    del self.claimed[username]
              if self.claimedMapFrame is not None and \
                 self.claimedMapFrame.username == username:
                    self.claimedMapFrame.setDirty()
           del self.jobs[id]


   def getClaimedUuids(self, username):
       uuids = []
       if username in self.claimed:
          for j in self.claimed[username]:
             urnuuid = j.uuid
             uuids.append(urnuuid[9:])
       return uuids

   def __getitem__(self,x):
       if x in self.jobs:
          return self.jobs[x]

       incompleteJobs = self.conn.getJobs(which_jobs='not-completed')
       if incompleteJobs.has_key(x):
          return Job(self.conn, x)
       else:
          return None
