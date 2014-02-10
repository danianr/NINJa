from Tkinter import *
from authdialog import AuthDialog
from mainscreen import MainScreen
from multicast import MulticastMember
from pageserver import PageServerAuth
from jobqueue import *
from cloudadapter import *
import cups
import re
import random




class Controller(object):
   def __init__(self, private, authname, public='public', tk=None):
      if tk != None: 
         self.tk = tk
      else:
         self.tk = Tk()
      self.tk['width'] = 1200
      self.tk['height'] = 1024

      self.publicName = public
      self.privateName = private
      self.loggedInUsername = None
      self.login = None
      self.mainscreen = None
      self.conn = cups.Connection() 
      self.selected = list()
      self.authorize = PageServerAuth(authname,  lambda: random.uniform(16, 4294967295) )
      unipattern = re.compile('(?!.{9})([a-z]{2,7}[0-9]{1,6})')
      self.mcast = MulticastMember('233.0.14.56', 34426, 7, unipattern)
      self.jobqueue = JobQueue(unipattern=unipattern, conn=self.conn,
                                           multicastHandler=self.mcast)
      self.nextQueueRefresh = self.tk.after_idle(self.updateQueue)
      self.cloudAdapter = CloudAdapter('/tmp/keepersock')

   def authCallback(self, username, result):
      self.lockQueue()
      self.login = None
      if result == True:
         self.loggedInUsername = username
         self.mainscreen = MainScreen(selectedList=self.selected,
                                      username=self.loggedInUsername,
                                      jobqueue=self.jobqueue,
                                      cloudAdapter=self.cloudAdapter,
                                      conn=self.conn,
                                      authHandler=self.authorize.authorizeJobs,
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
