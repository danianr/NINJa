import Tkinter
import cups
import re
import httplib
from time import time
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


   def authorizeJobs(self, selectedJobs, errorcb, authname):
       requestId=self.idGenerator()

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
          


   def releaseJob(self, job, requestId):

       sub = self.conn.createSubscription(self.privateUri, ['all'], lease_duration=630)
       if self.messageDisplay.messageFrame is None:
          print "a messageFrame MUST be registered with the MessageDisplay prior to job release"
          return
       else:
          mf = self.messageDisplay.messageFrame

       conn = self.conn
       timeout = -1
       check = -1

       # define a function to clean up in the event of a job hanging on the printer
       def jobTimeout():
           print "entering jobTimeout"
           mf.after_cancel(check)
           try:
              confirm = filter(lambda ev: (ev['notify-subscribed-event'] == 'job-completed' and
                                           ev['notify-job-id'] == job.jobId), conn.getNotifications([sub])['events'])
              if len(confirm) == 0:
                 conn.cancelJob(job.jobId, purgeJob=True)
              while len(confirm) == 0:
                 time.sleep(0.300);
                 confirm = filter(lambda ev: ( ev.has_key('notify-job-id') and ev.has_key('job-state') and
                                               ev['notify-job-id'] == job.jobId and ev['job-state'] > 6),
                                                                         conn.getNotifications([sub])['events'])
           except cups.IPPError:
               print 'caught an IPPError() while trying to print [%s]\n' % ( job.jobId, )
           finally:
               self.messageDisplay.messageFrame.event_generate('<<Finished>>')
               self.messageDisplay.releaseInterlock()


       # define a private function to check the notifications
       def checkNotifications():
             notifications = conn.getNotifications([sub])
             completed = filter(lambda ev: (ev['notify-subscribed-event'] == 'job-completed'), notifications['events'])
             completed = filter(lambda ev: (ev['notify-job-id'] == job.jobId), completed)
             if len(completed) == 0:
                mf.after(3000, checkNotifications)
             else:
                mf.after_cancel(timeout)
                conn.cancelSubscription(sub)
                attr = self.conn.getJobAttributes(job.jobId)
                self.messageDisplay.releaseInterlock()
                self.messageDisplay.messageFrame.event_generate('<<Finished>>')
                self.pageAccounting(self.hostname, job.username, requestId, attr['job-media-sheets-completed'])



       timeout = mf.after(600000, jobTimeout)
       check = mf.after(4000, checkNotifications)
       try:
          self.conn.moveJob(job_id=job.jobId, job_printer_uri=self.privateUri)
       except cups.IPPError:
          print 'print IPPError: \n' 
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
