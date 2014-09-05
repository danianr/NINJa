import Tkinter
import cups
import re
import httplib
import sys
import time
import xml.etree.ElementTree as ET


usernameKey = 'job-originating-user-name'
clientKey =   'job-originating-host-name'
titleKey = 'job-name'
uuidKey  = 'job-uuid'
supportedUriKey = 'printer-uri-supported'


class PageServerAuth(object):
   def __init__(self, private, hostname, idGenerator, display, conn):
       self.hostname   = hostname
       self.servername = 'wwwapp.cc.columbia.edu'
       self.idGenerator = idGenerator
       self.messageDisplay = display
       self.conn = conn
       printers = self.conn.getPrinters()
       self.privateUri = printers[private][supportedUriKey]
       self.currentJob = None				       # Support for event Handlers
       self.errorcb = None                                     # Support for event Handlers

   def authorizeJobs(self, selectedJobs, errorcb, authname):
       requestId=self.idGenerator()
       self.errorcb = errorcb

       for j in selectedJobs:
          self.messageDisplay.claimInterlock()
          url = '/atg/PageServer/query/%s/%s/%.5x/%d' % (self.hostname, authname, requestId, j.pages)
          http = httplib.HTTPSConnection(self.servername)
          http.request("GET", url)
          resp = http.getresponse()
          xml = resp.read()
          root = ET.fromstring(xml)
          queryResponse = root.find('queryResponse').attrib
          if queryResponse['Authorized'] == 'True':
               # reset the username on any authorized unclaimed job
               if j.username != authname:
                  j.username = authname
               self.releaseJob(j, queryResponse['reqId'])
          else:
               errorcb('Insufficient Quota')
               self.messageDisplay.quota(root, 'queryResponse', True)
               self.messageDisplay.releaseInterlock() 

          
   def cancelCurrentJob(self, event):
       print repr(event.__dict__)
       if ( self.currentJob is not None and self.messageDisplay.getInterlock() == '1' ):
          if self.errorcb is not None:
             self.errorcb("Canceling Print Job...")
          print >> sys.stderr, time.time(), 'User canceled job', self.currentJob.jobId
          self.conn.cancelJob(self.currentJob.jobId, purge_job=True)



   def releaseJob(self, job, requestId):

       self.currentJob = job
       sub = self.conn.createSubscription(self.privateUri, ['all'], lease_duration=630)
       if self.messageDisplay.messageFrame is None:
          print >> sys.stderr, time.time(), "a messageFrame MUST be registered with the MessageDisplay prior to job release"
          return
       else:
          mf = self.messageDisplay.messageFrame

       conn = self.conn
       timeout = -1
       check = -1

       # define a function to clean up in the event of a job hanging on the printer
       def jobTimeout():
           print >> sys.stderr, time.time(), "entering jobTimeout"
           mf.after_cancel(check)
           try:
              confirm = filter(lambda ev: (ev['notify-subscribed-event'] == 'job-completed' and
                                           ev['notify-job-id'] == job.jobId), conn.getNotifications([sub])['events'])
              if len(confirm) == 0:
                 conn.cancelJob(job.jobId, purge_job=True)
              while len(confirm) == 0:
                 time.sleep(0.300);
                 confirm = filter(lambda ev: ( ev.has_key('notify-job-id') and ev.has_key('job-state') and
                                               ev['notify-job-id'] == job.jobId and ev['job-state'] > 6),
                                                                         conn.getNotifications([sub])['events'])
           except cups.IPPError:
               print >> sys.stderr, time.time(), 'caught an IPPError() while trying to print [%s]\n' % ( job.jobId, )
           finally:
               self.currentJob = None
               if self.messageDisplay.messageFrame is not None:
                  self.messageDisplay.messageFrame.event_generate('<<Finished>>')
                  self.messageDisplay.releaseInterlock()


       # define a private function to check the notifications
       def checkNotifications():
          try:
             notifications = conn.getNotifications([sub])
             print repr(notifications['events'])
             completed = filter(lambda ev: (ev['notify-subscribed-event'] == 'job-completed'), notifications['events'])
             completed = filter(lambda ev: (ev['notify-job-id'] == job.jobId), completed)
             if len(completed) == 0:
                mf.after(3000, checkNotifications)
             else:
                mf.after_cancel(timeout)
                conn.cancelSubscription(sub)
                self.currentJob = None
                if self.messageDisplay.messageFrame is not None:
                   self.messageDisplay.releaseInterlock()
                   self.messageDisplay.messageFrame.event_generate('<<Finished>>')

                # Check for media-sheets first from the job, then from the event, and finally
                # just assume that our query count was correct (some drivers do not properly provide
                # page count information
                if completed[-1]['job-state-reasons'] == 'job-completed-successfully':
                   attr = self.conn.getJobAttributes(job.jobId)
                   print >> sys.stderr, time.time(), "attr['job-media-sheets-completed']",attr['job-media-sheets-completed']
                   print >> sys.stderr, time.time(), "completed[-1]['job-impressions-completed']", completed[-1]['job-impressions-completed']

                   if attr['job-media-sheets-completed'] != 0:
                      sheetsCompleted = attr['job-media-sheets-completed']
                      print >> sys.stderr, time.time(), 'using job-media-sheets-completed: ', sheetsCompleted
                   elif completed[-1]['job-impressions-completed'] != 0:
                      sheetsCompleted = completed[-1]['job-impressions-completed']
                      if attr.has_key('Duplex') and attr['Duplex'] == u'DuplexNoTumble':
                         sheetsCompleted = ( sheetsCompleted  + (sheetsCompleted % 2) ) / 2
                      print >> sys.stderr, time.time(), 'using job-impressions-completed: ', sheetsCompleted
                   else:
                      sheetsCompleted = job.pages
                      print >> sys.stderr, time.time(), 'falling back to job.pages:', sheetsCompleted
                else:
                   sheetsCompleted = 0
                   print >> sys.stderr, time.time(), 'using sheetsCompleted = 0'
                   
                   
                self.pageAccounting(self.hostname, job.username, requestId, sheetsCompleted)
          except cups.IPPError:
                print >> sys.stderr, time.time(), "caught an IPPError"

       timeout = mf.after(300000, jobTimeout)
       check = mf.after(4000, checkNotifications)
       try:
          self.conn.moveJob(job_id=job.jobId, job_printer_uri=self.privateUri)
       except cups.IPPError:
          print >> sys.stderr, time.time(), 'print IPPError: \n' 
          self.messageDisplay.releaseInterlock()
       


   def pageAccounting(self, hostname, username, requestId, sheets):
       url = '/atg/PageServer/deduct/%s/%s/%s/%d' % (hostname, username, requestId, sheets)
       http = httplib.HTTPSConnection(self.servername)
       http.request("GET", url)
       resp = http.getresponse()
       print resp.status, resp.reason
       xml = resp.read()
       root = ET.fromstring(xml)
       self.messageDisplay.quota(root, 'deductResponse')
       self.messageDisplay.bulletin(root, 'bulletin')
