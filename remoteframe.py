from Tkinter import *
from ttk import *
from os import popen
from jobqueue import *
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

       self.pack(expand=YES, fill=BOTH)
       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s %6s' % \
                             ( 'Id', 'User', 'Client', 'Title', 'Sheets'), font='TkFixedFont' )

       self.jobHeader.pack(expand=YES, fill=X, anchor=N)
       self.joblist = Listbox(master=self, font='TkFixedFont', height=40, width=60)
       self.joblist.pack(expand=YES, fill=BOTH, anchor=N)
       self.jobs = dict()
       self.currentDisplay = []

       self.joblist.bind('<Return>', self.handleAuth, add=True)
       self.unbind_all('<Key-Tab>')
       self.unbind_all('<Shift-Key-Tab>')
       switchToRemote = 'tk::TabToWindow [tk_focusNext %s]' % (self._w,)
       self.bind_all('<Key-Right>', switchToRemote, add=False)
       self.nextRefresh = self.after_idle(self.refresh)


   def handleAuth(self, event=None):

       self.after_cancel(self.nextRefresh)
       del self.selectedList[:]
       positionMapping=[]
       remoteJobIds = []
       filter(lambda (u, s, p, l): positionMapping.append(l), self.currentDisplay)
       for l in map(lambda x: positionMapping[int(x)], self.joblist.curselection() ):
           (uuid, printer, sha512, client, duplex, title) = self.jobs[l]
           print 'Adding remoteJob:(%s, %s, %s)  to selectedList' % (uuid, printer, sha512)
           if self.cloudAdapter.retrieveJob(self.loggedInUsername, sha512, gridlist):
              opts = dict()
              opts['job-originating-user-name'] = self.loggedInUsername
              opts['job-originating-host-name'] = client
              jobId = self.conn.printFile('remote', localfilename, title, opts)
              os.unlink(localfilename)
              remoteJobIds.add(jobId)
       self.selectedList = map(lambda i: self.jq[i], remoteJobIds)

       self.auth(self.selectedList, self.errorcb, self.loggedInUsername)
       self.nextRefresh = self.after_idle(self.refresh)


   def refresh(self, event=None):
       self.after_cancel(self.nextRefresh)
       remoteIndex = self.cloudAdapter.getIndex(self.loggedInUsername)
       if remoteIndex != self.currentDisplay:
          self.joblist.delete(0,len(self.jobs) )
          self.jobs.clear()
          if remoteIndex is not None:
             localjobs = set()
             localjobs.update(self.jq.getClaimedUuids(self.loggedInUsername))

             for (uuid, sha512, created, sheets, duplex, client, printer, username, title) in remoteIndex:
                 if uuid not in localjobs:
                    line = '%s  %s  %d   %s' % ( client, created.strftime('%a %I:%M:%S %p'), sheets, title[:32])
                    self.jobs[line] = (uuid, sha512, client, duplex, title)
                    self.joblist.insert(self.joblist.size(), line)
          self.joblist.update_idletasks()
          self.currentDisplay = remoteIndex
       self.event_generate('<<Bulletin>>')
       self.nextRefresh = self.after(1750, self.refresh)
