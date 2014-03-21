from Tkinter import *
from authdialog import AuthDialog
from mainscreen import MainScreen
from multicast import MulticastMember
from pageserver import PageServerAuth
from messagedisplay import MessageDisplay
from jobqueue import *
from cloudadapter import *
import cups
import re
import random
import time
import httplib
import xml.etree.ElementTree as ET





class Controller(object):
   def __init__(self, private, authname, public='public', tk=None):
      if tk != None: 
         self.tk = tk
      else:
         self.tk = Tk()
      self.tk['width'] = 1280
      self.tk['height'] = 1024

      self.publicName = public
      self.privateName = private
      self.loggedInUsername = None
      self.login = None
      self.mainscreen = None
      self.conn = cups.Connection() 
      self.messageDisplay = MessageDisplay()
      
      self.authorize = PageServerAuth(private, authname, lambda: random.uniform(16, 4294967295), 
                                      self.messageDisplay, self.conn)
      unipattern = re.compile('(?!.{9})([a-z]{2,7}[0-9]{1,6})')
      self.mcast = MulticastMember('233.0.14.56', 34426, 17, unipattern)
      self.jobqueue = JobQueue(unipattern=unipattern, conn=self.conn, multicastHandler=self.mcast)

      
      for attempts in range(3):
         try:
            self.cloudAdapter = CloudAdapter('/tmp/keepersock')
            break
         except OSError:
            self.daemonlog = file('multicast.log', mode='a', buffering=0)
            self.daemon = Popen('./multicast', stdin=None, stdout=self.daemonlog, stderr=STDOUT)
            time.sleep(1)


   def authCallback(self, username, result):
      self.login = None
      if result == True:
         self.loggedInUsername = username
         self.tk.wm_deiconify()
         self.mainscreen = MainScreen( username=self.loggedInUsername,
                                      jobqueue=self.jobqueue,
                                      cloudAdapter=self.cloudAdapter,
                                      conn=self.conn,
                                      authHandler=self.authorize.authorizeJobs,
                                      messageDisplay=self.messageDisplay,
                                      logoutCb=self.logoutCallback,
                                      master=self.tk)
         self.mainscreen.takefocus()
      else:
         self.loggedInUsername = None
         self.login = AuthDialog(self.authCallback, master=self.tk)


   def logoutCallback(self):
       self.mainscreen.destroy()
       self.mainscreen = None
       self.tk.bind_all('<Key-Tab>', 'tk::TabToWindow [tk_focusNext %W]', add=False)
       self.login = AuthDialog(self.authCallback, master=self.tk)
       self.login.takefocus()
       self.tk.wm_withdraw()


   def downloadBulletins(self, url):
         slash = url[8:].index('/') + 8
         servername = url[8:slash]
         http = httplib.HTTPSConnection(servername)
         http.request("GET", url)
         resp = http.getresponse()
         print resp.status, resp.reason
         xml = resp.read()
         print xml
         root = ET.fromstring(xml)
         self.messageDisplay.bulletin(root, 'bulletinBoard')
         self.messageDisplay.update()


   def start(self):
         self.conn.enablePrinter(self.privateName)
         self.conn.acceptJobs(self.privateName)
         self.conn.disablePrinter(self.publicName, reason="NINJa release required")
         self.conn.acceptJobs(self.publicName)
         print 'Starting Controller and accepting incoming jobs'
         self.login = AuthDialog(self.authCallback, master=self.tk)
         self.login.takefocus()
         self.tk.wm_withdraw()
         self.tk.mainloop()


   def stop(self):
         print 'Stopping Controller and rejecting incoming jobs'
         if self.mainscreen != None:
            self.mainscreen.destroy()
         if self.login != None:
            self.login.destroy()
         self.tk.destroy()
         self.conn.rejectJobs(self.publicName)
         self.conn.rejectJobs(self.privateName)
         self.conn.disablePrinter(self.privateName)
