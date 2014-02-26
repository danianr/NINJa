from Tkinter import *
from os import popen
from joblist import JobList
import cups
import re
from collections import deque


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



class JobQueue(object):
   def __init__(self, unipattern=None, conn=None, multicastHandler=None):
       if unipattern is None:
          self.unipattern=re.compile('.*')
       else:
          self.unipattern=unipattern
       if conn is None:
          self.conn = cups.Connection()
       else:
          self.conn = conn
       self.mcast=multicastHandler
       self.jobs=dict()
       self.claimed=dict()
       self.unclaimed=deque()


   def refresh(self, event=None):
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
          self.claimed[job.username].appendleft(job.jobId)
          if self.mcast is not None:
             self.mcast.advertise(job)
       else:
          self.unclaimed.appendleft(job.jobId)


   def remove(self, removedJobs):
       for n in filter( lambda x: x in self.jobs, removedJobs):
           if n in self.unclaimed:
              self.unclaimed.remove(n)
           else:
              username=self.jobs[n].username
              self.claimed[username].remove(n)
              if ( len(self.claimed[username]) == 0 ):
                 del self.claimed[username]
           del self.jobs[n]


   def getClaimedJobs(self, username):
       pairs = []
       if username in self.claimed:
          pairs.extend(map(lambda x: (x, self.jobs[x]), self.claimed[username]))
       print pairs
       return pairs

   def getClaimedUuids(self,username):
       uuids = []
       if username in self.claimed:
          for jobid in self.claimed[username]:
             urnuuid = self.jobs[jobid].uuid
             uuids.append(urnuuid[9:])
       print uuids
       return uuids


   def getUnclaimedJobs(self):
       pairs = []
       if len(self.unclaimed) > 0:
          pairs.extend(map(lambda x: (x, self.jobs[x]), self.unclaimed))
       return pairs
