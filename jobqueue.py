from Tkinter import *
from os import popen
from joblist import JobList
import cups
import re
from collections import deque
import time


class Job(object):
   def __init__(self, conn=None, jobId=None):
       self.jobId = jobId
       self.authenticated = False
       printerUri = conn.getJobAttributes(jobId).get('printer-uri')

       # This will raise an IPPError if the job has not finished transferring
       # in the form of IPPError: (1030, 'client-error-not-found')
       doc = conn.getDocument(printerUri, jobId, 1)

       # Note that the getDocument command must be issued prior to requesting
       # detailed job attributes such as document-format, job-originating-host-name
       # and job-originating-user-name, otherwise these attributes will be blank
       digest_cmd = '/usr/bin/openssl dgst -sha512 %s' % ( doc['file'] )
       pagecount_cmd = './pagecount.sh %s %s' % ( doc['document-format'], doc['file'] )
       sha512 = popen(digest_cmd).read()
       pagecount = popen(pagecount_cmd).read()
       self.pages = int(pagecount)
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

       if ( attr.has_key('Duplex')  and attr['Duplex'] == u'DuplexNoTumble' ):
           self.duplex = True
	   self.pages = self.pages % 2 + self.pages / 2
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
       return '%4d  %-12s %-18s %-48s  %6s' % ( self.jobId,  self.username, self.hostname, self.displayTitle, self.pages )



class JobMapping(object):
   # Takes a sequence of Job objects, produces an iterator
   # suitable for supplying to a a listbox (textual description)
   # and allows direct access to Job objects based on their
   # position.  Also takes a list of positions and returns
   # a tuple of Job objects associated with each

   def __init__(self, iterable):
       self.timestamp = time.time()
       self.internal = list()
       self.internal.extend(iterable)
       self.dirty = False

   def isDirty(self):
       return self.dirty

   def setDirty(self):
       self.dirty = True

   def map(self, iterable):
       return map(lambda i: self.internal[i], iterable)


   # Only define getter accessors since this is technically
   # a read-only snapshot
   def __getitem(self, x)__:
       return self.internal[x]

   def __getslice__(self, x, y):
       return self.internal[x:y]

   def __iter__(self):
       return iter(map(lambda j: j.__str__, self.internal))


class JobQueue(object):
   def __init__(self, unipattern, conn, multicastHandler=None):
       self.unipattern = unipattern
       self.conn       = conn
       self.mcast      = multicastHandler
       self.jobs       = dict()
       self.claimed    = dict()
       self.unclaimed  = deque()
       self.refreshReq = deque()
       self.claimedMapFrame   = None
       self.unclaimedMapFrame = None
       self.mimimumRefreshPeriod = 45	# seconds


   def getMapping(username=None):
       if username is None:
          if self.unclaimedFrame is None or 
             self.unclaimedFrame.isDirty():
               self.refresh()
               self.unclaimedMapFrame = JobMapping(self.unclaimed)
          return self.unclaimedMapFrame
       else:
          if self.claimedFrame is None or 
             self.claimedFrame.isDirty() or
             self.claimedFrame.username != username:
               self.refresh()
               self.claimedMapFrame = JobMapping(self.claimed[username])
          return self.claimedMapFrame
            

   def refresh(self, event=None):
       now = time.time()
       self.refreshReq.append(now)
       for req in self.refreshReq:
          if (req + self.delay) < now:
             break
       else:
          return
       incompleteJobs = self.conn.getJobs(which_jobs='not-completed')
       self.remove( filter( lambda x: not incompleteJobs.has_key(x), self.jobs.keys()) )
       for jobId in filter( lambda x: not self.jobs.has_key(x), incompleteJobs.keys()):
          try:
             j = Job(self.conn, jobId )
             self.add(j)
          except cups.IPPError as e:
             print("caught an IPPError",e)
             continue


   def add(self, job):
       self.jobs[job.jobId] = job
       if self.unipattern.match(job.username):
          if job.username not in self.claimed:
             self.claimed[job.username] = deque()
          self.claimed[job.username].appendleft(job)
          if self.claimedFrame is not None and
             self.claimedFrame.username == job.username:
                self.claimedFrame.setDirty()
          if self.mcast is not None:
             self.mcast.advertise(job)
       else:
          self.unclaimed.appendleft(job)
          if self.unclaimedFrame is not None:
             self.unclaimedFrame.setDirty()


   def remove(self, removedJobs):
       for n in filter( lambda x: x in self.jobs, removedJobs):
           if n in self.unclaimed:
              self.unclaimed.remove(n)
              if self.unclaimedFrame is not None:
                 self.unclaimedFrame.setDirty()
           else:
              username=self.jobs[n].username
              self.claimed[username].remove(n)
              if ( len(self.claimed[username]) == 0 ):
                 del self.claimed[username]
              if self.claimedFrame is not None and
                 self.claimedFrame.username == username:
                    self.claimedFrame.setDirty()
           del self.jobs[n]


   def getClaimedUuids(self,username):
       uuids = []
       if username in self.claimed:
          for j in self.claimed[username]:
             urnuuid = j.uuid
             uuids.append(urnuuid[9:])
       return uuids
