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
   def __init__(self, hostname, conn=None):
       self.hostname   = hostname
       self.servername = 'wwwapp.cc.columbia.edu'
       private    = 'watson8_printer_atg_columbia_edu'
       if conn is None:
          self.conn = cups.Connection()
       else:
          self.conn = conn
       printers = self.conn.getPrinters()
       self.privateUri = printers[private][supportedUriKey]


   def authorizeJobs(self, selectedJobs):
       print 'Entering authorizeJobs'
       print repr(selectedJobs)
       requestId=746125

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
               error_message('Releasing jobId:%s' % (j.jobId,))
               self.releaseJob(j, queryResponse['reqId'])
          else:
               error_message('Insufficient Quota')


   def releaseJob(self, job, requestId):

       self.conn.moveJob(job_id=job.jobId, job_printer_uri=self.privateUri)
       waiting = True
       while waiting:
           attr = conn.getJobAttributes(job.jobId)
           if attr['time-at-completed'] is not None:
              waiting = False
              if attr['job-state-reasons'] == 'job-completed-successfully':
                 url = '/atg/PageServer/deduct/%s/%s/%s/%d' % (self.hostname, job.username,
                                               requestId, attr['job-media-sheets-completed'])
              else:
                 error_message("There was a problem printing your document")
                 
                 
       http = httplib.HTTPSConnection(self.servername)
       http.request("GET", url)
       resp = http.getresponse()
       print resp.status, resp.reason
       xml = resp.read()
       print xml
       root = ET.fromstring(xml)
       deductResponse = root.find('deductResponse').attrib
