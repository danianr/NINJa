from jobqueue import Job, JobQueue

class MockJob(Job):

   # Only the init function needs reimplmentation, the __cmp__  /
   # __str__  /  __repr__ methods  should be allowed to be inherited from
   # the actual Job class; note that  not all fields are reproducted, just
   # those used by the inherieted methods
   def __init__(self, jobId, uuid, sha512, username, creation, pagecount, client, title, duplex=False, state=3):
        self.__hash__ = lambda: jobId
        self.jobId = jobId
	self.printerUri = printerUri
	self.uuid = uuid
	self.sha512 = sha512
	self.username = username
	self.creation = creation
	self.pagecount = pagecount
	self.client = client
	self.title = title
	self.duplex = duplex
	self.jobState = state
	self.displayTitle = self.title[:47]

class MockQueue(JobQueue):

   def __init__(self, unipattern=None, conn=None, multicastHandler=None):
       if unipattern is not None:
          self.unipattern = unipattern
       else:
          self.unipattern = re.compile('.*')
       self.conn = None
       self.mcast = None


   def refresh(self):
       print "refresh called"

