from Tkinter import *
from ttk import *
from jobqueue import *
from cloudadapter import IndexView
import os
import time
import cups


class RemoteFrame(Frame):

   def __init__(self, username, jobqueue, cloudAdapter, conn, authHandler, errorcb, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.selectedList     = []
       self.loggedInUsername = username
       self.jq               = jobqueue
       self.cloudAdapter     = cloudAdapter
       self.auth    = authHandler
       self.errorcb = errorcb
       self.conn    = conn
       self.remoteIndex = IndexView(username, cloudAdapter.getIndex, cloudAdapter.indexStr)
       self.viewTimestamp = 1

       self.pack(expand=YES, fill=BOTH)
       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s %6s' % \
                             ( 'Id', 'User', 'Client', 'Title', 'Sheets'), font='TkFixedFont' )

       self.jobHeader.pack(expand=YES, fill=X, anchor=N)
       self.joblist = Listbox(master=self, background='white', font='TkFixedFont', height=40, width=60)
       self.joblist.pack(expand=YES, fill=BOTH, anchor=N)
       self.jobs = dict()
       self.currentDisplay = []

       self.joblist.bind('<Return>', self.handleAuth, add=True)
       #self.unbind_all('<Key-Tab>')
       #self.unbind_all('<Shift-Key-Tab>')
       switchToRemote = 'tk::TabToWindow [tk_focusNext %s]' % (self._w,)
       self.bind_all('<Key-Right>', switchToRemote, add=False)
       self.nextRefresh = self.after_idle(self.refresh)


   def handleAuth(self, event=None):

       self.after_cancel(self.nextRefresh)
       del self.selectedList[:]
       remoteJobIds = set()
       for i in self.joblist.curselection():
           (uuid, sha512, created, sheets, duplex, client, printer, username, title) = self.remoteIndex[int(i)]
           if self.cloudAdapter.retrieveJob(self.loggedInUsername, sha512):
              opts = dict()
              opts['job-originating-user-name'] = self.loggedInUsername
              opts['job-originating-host-name'] = client
              localfilename = '/tmp/' + sha512
              jobId = self.conn.printFile('remote', localfilename, title, opts)
              os.unlink(localfilename)
              remoteJobIds.add(jobId)
       self.selectedList = map(lambda j: self.jq[j], remoteJobIds)
       self.auth(self.selectedList, self.errorcb, self.loggedInUsername)
       self.nextRefresh = self.after_idle(self.refresh)


   def refresh(self, event=None):
       self.after_cancel(self.nextRefresh)
       self.remoteIndex.refresh()
       if self.remoteIndex.timestamp != self.viewTimestamp:
          self.viewTimestamp = self.remoteIndex.timestamp
          self.joblist.delete(0,self.joblist.size())
          if self.remoteIndex is not None:
             #localjobs = set()
             #localjobs.update(self.jq.getClaimedUuids(self.loggedInUsername))

             for line in self.remoteIndex:
                 self.joblist.insert(self.joblist.size(), line)
          self.joblist.update_idletasks()

       # Update the message display pane 
       self.event_generate('<<Bulletin>>')
       self.nextRefresh = self.after(1750, self.refresh)
