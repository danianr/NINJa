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
       print 'Entering authorizeJobs'
       print 'PRINT_INTERLOCK = %s' % (self.messageDisplay.getInterlock(),)
       print repr(selectedJobs)
       requestId=self.idGenerator()

       for j in selectedJobs:
          self.messageDisplay.claimInterlock()
          print 'PRINT_INTERLOCK = %s' % (self.messageDisplay.getInterlock(),)
          url = '/atg/PageServer/query/%s/%s/%.5x/%d' % (self.hostname, authname, requestId, j.pages)
          http = httplib.HTTPSConnection(self.servername)
          http.request("GET", url)
          resp = http.getresponse()
          print resp.status, resp.reason
          xml = resp.read()
          root = ET.fromstring(xml)
          queryResponse = root.find('queryResponse').attrib
          if queryResponse['Authorized'] == 'True':
               # reset the username on any authorized unclaimed job
               if j.username != authname:
                  j.username = authname
               self.releaseJob(j, queryResponse['reqId'], errorcb, authname)
          else:
               errorcb('Insufficient Quota')
               self.messageDisplay.quota(root, 'queryResponse', True)
          self.messageDisplay.releaseInterlock()


   def releaseJob(self, job, requestId, errorcb, authname):
       try:
          self.conn.moveJob(job_id=job.jobId, job_printer_uri=self.privateUri)
          # dear god no, not a busy while loop.  there has to be a subscription / event
          # driven fix that will handle this better.  Left in for now, in the interest
          # of rapid prototyping (because errors never happen in demos)
          waiting = True
          print "time-at-startjob:", time()
          while waiting:
              attr = self.conn.getJobAttributes(job.jobId)
              print "time-at-completed: ",repr(attr['time-at-completed'])
              if attr['time-at-completed'] is not None:
                 waiting = False
                 if attr['job-state-reasons'] == 'job-completed-successfully':
                    url = '/atg/PageServer/deduct/%s/%s/%s/%d' % (self.hostname, job.username,
                                               requestId, attr['job-media-sheets-completed'])
                 else:
                    errorcb("There was a problem printing your document")
                    return
                 self.messageDisplay.messageFrame.event_generate('<<Finished>>')
       except:
          ( exc_type, exc_value, exc_traceback ) = sys.exc_info()
          print exc_type
          print exc_value
          print repr(exc_value)
          print exc_traceback
          #errorcb('IPPError %d: %s' % (status, description) )
          return
                 
       http = httplib.HTTPSConnection(self.servername)
       http.request("GET", url)
       resp = http.getresponse()
       print resp.status, resp.reason
       xml = resp.read()
       root = ET.fromstring(xml)
       self.messageDisplay.quota(root, 'deductResponse')
       self.messageDisplay.bulletin(root, 'bulletin')
