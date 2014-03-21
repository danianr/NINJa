from Tkinter import *
from ttk import *
from os import popen
from jobqueue import *
import time
import cups



class MainScreen(Frame):
   def __init__(self, username, jobqueue, cloudAdapter, conn,
                  authHandler,  messageDisplay, logoutCb, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.pack(expand=YES, fill=BOTH)
       self.tk  = master
       self.notebook = Notebook(master=self)
       self.instructions = StringVar()
       self.instructions.set('Left arrow selects Local jobs, Right arrow selects remote jobs, Enter prints')
       self.messageDisplay = messageDisplay
       self.instrbar = Label(textvar=self.instructions, master=self)
       self.instrbar.pack(side=BOTTOM, fill=X, expand=N)
       self.hpane = PanedWindow(orient=HORIZONTAL, width=1180,height=940)
       self.vpane = PanedWindow(orient=VERTICAL,width=560,height=940)
       self.mdisplay = Frame()
       self.messageDisplay.registerMessageFrame(self.mdisplay)
       self.messageDisplay.registerErrorCallback(self.errorCallback)

       self.local = LocalFrame(username, jobqueue, conn, authHandler, self.errorCallback)
       self.remote = RemoteFrame(username, jobqueue, cloudAdapter, conn, authHandler, self.errorCallback)
       self.hpane.add(self.local)
       self.vpane.add(self.remote)
       self.vpane.add(self.mdisplay)
       self.hpane.add(self.vpane)
       self.notebook.add(self.hpane)
       self.notebook.tab(0, text=username)
       self.unclaimed = UnclaimedFrame(username, jobqueue, conn, authHandler, self.errorCallback)
       self.notebook.add(self.unclaimed)
       self.notebook.tab(1, text="Unclaimed jobs")
       self.notebook.pack(side=TOP, fill=BOTH, expand=Y)
       self.unbind_class('TNotebook', '<Control-Shift-Key-Tab>')
       self.unbind_class('TNotebook', '<Control-Key-Tab>')
       self.unbind_class('TNotebook', '<Key-Left>')
       self.unbind_class('TNotebook', '<Key-Right>')
       self.unbind_class('Panedwindow', '<Leave>')
       self.unbind_class('Panedwindow', '<Button-1>')
       self.unbind_class('Panedwindow', '<Button-2>')
       self.unbind_class('Panedwindow', '<B1-Motion>')
       self.unbind_class('Panedwindow', '<B2-Motion>')
       self.unbind_class('Panedwindow', '<ButtonRelease-1>')
       self.unbind_class('Panedwindow', '<ButtonRelease-2>')
       self.unbind_class('Panedwindow', '<Motion>')
       self.unbind_class('Listbox', '<Key-Left>')
       self.unbind_class('Listbox', '<Key-Right>')

       self.logoutCb = logoutCb

       self.bind_all('<Key-Tab>', self.switchView )
       self.bind_all('<Key-Escape>', self.logout )
       self.jobWidget =  ( self.local.joblist, self.unclaimed.joblist )
       self.tk.update_idletasks()

   def errorCallback(self, message):
       err = Toplevel(master=self.tk)
       errlabel = Label(text=message, master=err)
       errlabel.pack()
       err.pack()
       print "Error: %s" % (message,)
       self.tk.update_idletasks()
       err.after(6000, err.destroy)

   def switchView(self, e):
       if isinstance(e.widget, Listbox):
          e.widget.selection_clear(0, 'end')
       current = self.notebook.select()
       nexttab = ( self.notebook.index(current) + 1 ) % self.notebook.index('end')
       self.notebook.select(nexttab)
       self.jobWidget[nexttab].focus_set()

   def takefocus(self):
       if self.local is not None and self.local.joblist is not None:
             self.local.joblist.focus_set()


   def setInstructions(self, instructions):
       self.instrbar.set(instructions)

   def getMessageDisplay(self):
       return self.mdisplay

   def logout(self, e):
       self.unbind_all('<Key-Tab>')
       self.unbind_all('<Key-Escape>')
       self.unclaimed.destroy()
       self.vpane.destroy()
       self.hpane.destroy()
       self.notebook.destroy()
       self.instrbar.destroy()
       self.logoutCb()


class LocalFrame(Frame):
   def __init__(self, username, jobqueue, conn, authHandler, errorcb, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.loggedInUsername = username
       self.jq      = jobqueue
       self.conn    = conn
       self.auth    = authHandler
       self.errorcb = errorcb

       self.pack(expand=YES, fill=BOTH)
       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s %6s' % \
                             ( 'Id', 'User', 'Client', 'Title', 'Sheets'), font='TkFixedFont' )
       self.jobHeader.pack(expand=YES, fill=X, anchor=N)
       self.joblist = Listbox(master=self, height=60, width=60,font='TkFixedFont')
       self.joblist.pack(expand=YES, fill=BOTH, anchor=N)

       # Key Bindings
       self.joblist.bind('<Return>', self.handleAuth, add=True)
       switchToLocal = 'tk::TabToWindow [tk_focusNext %s]' % (self._w,)
       self.unbind_all('<Key-Tab>')
       self.unbind_all('<Shift-Key-Tab>')
       self.bind_all('<Key-Left>', switchToLocal, add=False)

       self.jobMapping = None
       self.nextRefresh = self.after_idle(self.refresh)
       self.update_idletasks()


   def handleAuth(self, event=None):
       self.after_cancel(self.nextRefresh)
       selectedList = self.jobMapping.map(self.joblist.curselection())
       self.auth(selectedList, self.errorcb)
       self.nextRefresh = self.after_idle(self.refresh)


   def refresh(self, event=None):
       self.after_cancel(self.nextRefresh)
       mapping = self.jq.getMapping(self.loggedInUsername)
       if self.jobMapping != mapping:
          if self.jobMapping is not None:
             self.joblist.delete(0, len(self.jobMapping) )
          if mapping is not None:
             for text in mapping:
                self.joblist.insert(self.joblist.size(), text)
          self.jobMapping = mapping
          self.joblist.update_idletasks()
       self.nextRefresh = self.after(850, self.refresh)



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

       self.auth(self.selectedList, self.errorcb)
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



class UnclaimedFrame(Frame):
   def __init__(self, username, jobqueue, conn, authHandler, errorcb, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.loggedInUsername = username
       self.jq               = jobqueue
       self.conn             = conn
       self.auth             = authHandler
       self.errorcb          = errorcb

       self.pack(expand=YES, fill=BOTH)
       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s %6s' % \
                             ( 'Id', 'User', 'Client', 'Title', 'Sheets'), font='TkFixedFont' )
       self.jobHeader.pack(expand=YES, fill=X, anchor=N)
       self.joblist = Listbox(master=self, height=60, width=60,font='TkFixedFont')
       self.joblist.pack(expand=YES, fill=X, anchor=N)
       self.joblist.bind('<Return>', self.handleAuth, add=True)

       self.jobMapping  = None
       self.nextRefresh = self.after_idle(self.refresh)


   def handleAuth(self, event=None):
       self.after_cancel(self.nextRefresh)
       selectedList = self.jobMapping.map(self.joblist.curselection())
       self.auth(selectedList, self.errorcb, username=self.loggedInUsername)
       self.nextRefresh = self.after_idle(self.refresh)


   def refresh(self, event=None):
       self.after_cancel(self.nextRefresh)
       mapping = self.jq.getMapping()
       if self.jobMapping != mapping:
          if self.jobMapping is not None:
             self.joblist.delete(0, len(self.jobMapping) )
          if mapping is not None:
             for text in mapping:
                self.joblist.insert(self.joblist.size(), text)
          self.jobMapping = mapping
          self.joblist.update_idletasks()
       self.nextRefresh = self.after(1150, self.refresh)
