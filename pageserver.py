import Tkinter
import cups
import re
import httplib
import xml.etree.ElementTree as ET


usernameKey = 'job-originating-user-name'
clientKey =   'job-originating-host-name'
titleKey = 'job-name'
uuidKey  = 'job-uuid'
supportedUriKey = 'printer-uri-supported'

class PageServerAuth(object):
   def __init__(self, hostname, idGenerator, conn=None):
       self.hostname   = hostname
       self.servername = 'wwwapp.cc.columbia.edu'
       self.idGenerator = idGenerator
       private    = 'private'
       if conn is None:
          self.conn = cups.Connection()
       else:
          self.conn = conn
       printers = self.conn.getPrinters()
       self.privateUri = printers[private][supportedUriKey]


   def authorizeJobs(self, selectedJobs, errorcb):
       print 'Entering authorizeJobs'
       print repr(selectedJobs)
       requestId=self.idGenerator()

       for j in selectedJobs:
          url = '/atg/PageServer/query/%s/%s/%.5x/%d' % (self.hostname, j.username, requestId, j.pages)
          http = httplib.HTTPSConnection(self.servername)
          http.request("GET", url)
          resp = http.getresponse()
          print resp.status, resp.reason
          xml = resp.read()
          root = ET.fromstring(xml)
          queryResponse = root.find('queryResponse').attrib
          if queryResponse['Authorized'] == 'True':
               self.releaseJob(j, queryResponse['reqId'], errorcb)
          else:
               errorcb('Insufficient Quota')


   def releaseJob(self, job, requestId, errorcb):

       self.conn.moveJob(job_id=job.jobId, job_printer_uri=self.privateUri)
       # dear god no, not a busy while loop.  there has to be a subscription / event
       # driven fix that will handle this better.  Left in for now, in the interest
       # of rapid prototyping (because errors never happen in demos)
       waiting = True
       while waiting:
           attr = self.conn.getJobAttributes(job.jobId)
           if attr['time-at-completed'] is not None:
              waiting = False
              if attr['job-state-reasons'] == 'job-completed-successfully':
                 url = '/atg/PageServer/deduct/%s/%s/%s/%d' % (self.hostname, job.username,
                                               requestId, attr['job-media-sheets-completed'])
              else:
                 errorcb("There was a problem printing your document")
                 
                 
       http = httplib.HTTPSConnection(self.servername)
       http.request("GET", url)
       resp = http.getresponse()
       print resp.status, resp.reason
       xml = resp.read()
       print xml
       root = ET.fromstring(xml)
       deductResponse = root.find('deductResponse').attrib
