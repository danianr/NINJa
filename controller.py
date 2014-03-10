from Tkinter import *
from authdialog import AuthDialog
from mainscreen import MainScreen
from multicast import MulticastMember
from pageserver import PageServerAuth
from MessageDisplay import MessageDisplay
from jobqueue import *
from cloudadapter import *
import cups
import re
import random
import time




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
      self.selected = list()
      self.messageDisplay = MessageDisplay()
      self.authorize = PageServerAuth(private, authname, lambda: random.uniform(16, 4294967295), 
                                      self.messageDisplay, self.conn)
      unipattern = re.compile('(?!.{9})([a-z]{2,7}[0-9]{1,6})')
      self.mcast = MulticastMember('233.0.14.56', 34426, 17, unipattern)
      self.jobqueue = JobQueue(unipattern=unipattern, conn=self.conn,
                                           multicastHandler=self.mcast)
      self.nextQueueRefresh = self.tk.after_idle(self.updateQueue)

      
      for attempts in range(3):
         try:
            self.cloudAdapter = CloudAdapter('/tmp/keepersock')
            break
         except OSError:
            self.daemonlog = file('multicast.log', mode='a', buffering=0)
            self.daemon = Popen('./multicast', stdin=None, stdout=self.daemonlog, stderr=STDOUT)
            time.sleep(1)


   def authCallback(self, username, result):
      self.lockQueue()
      self.login = None
      if result == True:
         self.loggedInUsername = username
         self.tk.wm_deiconify()
         self.mainscreen = MainScreen(selectedList=self.selected,
                                      username=self.loggedInUsername,
                                      jobqueue=self.jobqueue,
                                      cloudAdapter=self.cloudAdapter,
                                      conn=self.conn,
                                      authHandler=self.authorize.authorizeJobs,
                                      messageDisplay=self.messageDisplay,
                                      logoutCb=self.logoutCallback,
                                      lockQueue=self.lockQueue,
                                      unlockQueue=self.unlockQueue,
                                      updateQueue=self.updateQueue,
                                      master=self.tk)

      else:
         self.unlockQueue()
         self.loggedInUsername = None
         self.login = AuthDialog(self.authCallback, master=self.tk)

   def logoutCallback(self):
       self.mainscreen.destroy()
       self.mainscreen = None
       self.unlockQueue()
       self.login = AuthDialog(self.authCallback, master=self.tk)
       self.tk.wm_withdraw()
       print self.login.bindtags()
       print self.login.bind('<Key-Tab>')
       print '=======[ Toplevel ]======='
       print self.login.bind_class('Toplevel')
       for k in self.login.bind_class('Toplevel'):
          print '----> Binding: %s' % (k,)
          print self.login.bind_class('Toplevel', k )
       print '========[ Entry ]========='
       print self.login.bind_class('Entry')
       for k in self.login.bind_class('Entry'):
          print '----> Binding: %s' % (k,)
          print self.login.bind_class('Entry', k )



   def lockQueue(self):
      if self.nextQueueRefresh is not None:
         self.tk.after_cancel(self.nextQueueRefresh)
      self.nextQueueRefresh = None
         

   def unlockQueue(self):
      if self.nextQueueRefresh is not None:
         self.tk.after_cancel(self.nextQueueRefresh)
      self.nextQueueRefresh = self.tk.after_idle(self.updateQueue)

   def updateQueue(self):
      if self.nextQueueRefresh is not None:
         self.tk.after_cancel(self.nextQueueRefresh)
      self.jobqueue.refresh()
      self.nextQueueRefresh = self.tk.after(4000, self.updateQueue)

   def start(self):
         #self.conn.enablePrinter(self.privateName)
         #self.conn.acceptJobs(self.publicName)
         print 'Starting Controller and accepting incoming jobs'
         self.login = AuthDialog(self.authCallback, master=self.tk)
         self.tk.wm_withdraw()
         print self.login.bindtags()
         print self.login.bind('<Key-Tab>')
         print '=======[ Toplevel ]======='
         print self.login.bind_class('Toplevel')
         for k in self.login.bind_class('Toplevel'):
            print '----> Binding: %s' % (k,)
            print self.login.bind_class('Toplevel', k )
         print '========[ Entry ]========='
         print self.login.bind_class('Entry')
         for k in self.login.bind_class('Entry'):
            print '----> Binding: %s' % (k,)
            print self.login.bind_class('Entry', k )
         self.tk.mainloop()

   def stop(self):
         print 'Stopping Controller and rejecting incoming jobs'
         if self.mainscreen != None:
            self.mainscreen.destroy()
         if self.login != None:
            self.login.destroy()
         self.tk.destroy()
         #self.conn.rejectJobs(self.publicName)
         #self.conn.disablePrinter(self.privateName)
