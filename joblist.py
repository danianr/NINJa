from collections import deque

class JobList(object):

   def __init__(self, jobMap=None, initial=None):
      self.jobs = dict()
      self.merged= deque()

      if type(jobMap) is dict:
         for (user, prev) in jobMap.iteritems(): 
	     assert type(prev) is list
             self.jobs[user] = prev

         if initial is None:
            self.merged.extendleft(jobs)

      if type(initial) is deque:   
         self.merged.extend(initial)


   def add(self, username, jobId):

      if username in self.jobs:
         for n in filter( lambda x: x in self.merged, self.jobs[username]):
            self.merged.remove(n)

         self.jobs[username].append(jobId)

      else:
         self.jobs[username] = [jobId]

      self.merged.extendleft(self.jobs[username])


   def remove(self, removedJobs):

       for n in filter( lambda x: x in self.merged, removedJobs):
          self.merged.remove(n)

       for jobseq in self.jobs.values():
         map( jobseq.remove, filter( lambda x: x in jobseq, removedJobs) )


   def __iter__(self):
      return iter(self.merged)

   def __getitem__(self, n):
      return self.merged[n]

   def __getslice__(self, i, j):
      return self.merged[i:j]

   def __delitem__(self, n):
      self.remove([n])

   def __delslice__(self, i, j):
      self.remove(self, self.merged[i:j])

   def __repr__(self):
      return "JobList( jobMap=%s, initial=%s )" % \
                            (repr(self.jobs), repr(self.merged) )

   def __str__(self):
      return "%s" % list(self.merged)
