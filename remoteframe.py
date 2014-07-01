from Tkinter import *
from ttk import *
from jobqueue import *
from cloudadapter import IndexView
import os
import time
import cups


class RemoteFrame(Frame):

   def __init__(self, username, jobqueue, cloudAdapter, conn, authHandler, errorcb, resetAutologout,
                                                                                 master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.selectedList     = []
       self.loggedInUsername = username
       self.jq               = jobqueue
       self.cloudAdapter     = cloudAdapter
       self.auth             = authHandler
       self.errorcb          = errorcb
       self.resetAutologout  = resetAutologout
       self.conn             = conn
       self.remoteIndex      = IndexView(username, cloudAdapter.getIndex, cloudAdapter.indexStr)
       self.viewTimestamp    = 1

       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s   %6s' % \
                             ( 'Id', 'User', 'Client', 'Title', 'Sheets'), padx='4', anchor='sw', font='TkFixedFont' )

       self.jobHeader.place(in_=self, x=0, y=30, width=self['width'], height=30, anchor='sw')

       self.joblist = Listbox(master=self, background='white', font='TkFixedFont', selectbackground='#007333', selectforeground='white', highlightthickness='3', highlightcolor='#75AADB')

       self.joblist.place(in_=self, x=0, y=30, width=self['width'], height=self['height'] - 30, anchor='nw')
       self.pack()
       self.jobs = dict()
       self.currentDisplay = []

       self.joblist.bind('<Return>', self.handleAuth, add=True)
       self.event_add('<<RemoteJobs>>', '<Key-Right>')

       self.nextRefresh = self.after_idle(self.refresh)


   def handleAuth(self, event=None):
       if self.getvar('PRINT_INTERLOCK') == '1':
          return
       self.event_generate('<<Printing>>')
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
       self.resetAutologout(45)
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
