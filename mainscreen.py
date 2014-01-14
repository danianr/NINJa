from Tkinter import *
from ttk import *
from os import popen
from jobqueue import *
import cups



class MainScreen(Frame):
   def __init__(self, selectedList, username, jobqueue, cloudAdapter, conn=None,
                  authHandler=None,  logoutCb=None, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.pack(expand=YES, fill=BOTH)
       self.notebook = Notebook(master=self)
       self.instructions = StringVar()
       self.instructions.set('Left arrow selects Local jobs, Right arrow selects remote jobs, Enter prints')
       self.messages = StringVar()
       self.messages.set('Hello World!')
       self.instrbar = Label(textvar=self.instructions, master=self)
       self.instrbar.pack(side=BOTTOM, fill=X, expand=N)
       self.hpane = PanedWindow(orient=HORIZONTAL, width=1180,height=940)
       self.vpane = PanedWindow(orient=VERTICAL,width=560,height=940)
       self.mdisplay = Label(textvar=self.messages)
       self.local = LocalFrame(selectedList, username, jobqueue, conn, authHandler)
       self.remote = RemoteFrame(selectedList, username, cloudAdapter, conn, authHandler)
       self.hpane.add(self.local)
       self.vpane.add(self.remote)
       self.vpane.add(self.mdisplay)
       self.hpane.add(self.vpane)
       self.notebook.add(self.hpane)
       self.notebook.tab(0, text=username)
       self.unclaimed = UnclaimedFrame(selectedList, username, jobqueue, conn, authHandler)
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

   def switchView(self, e):
       if isinstance(e.widget, Listbox):
          e.widget.selection_clear(0, 'end')
       current = self.notebook.select()
       nexttab = ( self.notebook.index(current) + 1 ) % self.notebook.index('end')
       self.notebook.select(nexttab)
       self.jobWidget[nexttab].focus_set()


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
   def __init__(self, selectedList, username, jobqueue,
                 conn=None, authHandler=None, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.jq = jobqueue
       self.pack(expand=YES, fill=BOTH)
       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s %6s' % ( 'Id', 'User', 'Client', 'Title', 'Sheets'), font='TkFixedFont' )
       self.jobHeader.pack(expand=YES, fill=X, anchor=N)
       self.joblist = Listbox(master=self, height=60, width=60,font='TkFixedFont')
       self.joblist.pack(expand=YES, fill=BOTH, anchor=N)
       self.selectedList = selectedList
       self.auth=authHandler
       if conn is None:
          self.conn = cups.Connection()
       else:
          self.conn = conn
       self.jobs = dict()
       self.currentDisplay = []
       self.loggedInUsername=username
       self.jq.refresh()
       self.nextRefresh = self.after_idle(self.refresh)
       self.joblist.bind('<Return>', self.handleAuth, add=True)
       switchToLocal = 'tk::TabToWindow [tk_focusNext %s]' % (self._w,)
       self.unbind_all('<Key-Tab>')
       self.unbind_all('<Shift-Key-Tab>')
       self.bind_all('<Key-Left>', switchToLocal, add=False)


   def handleAuth(self, event=None):
       self.after_cancel(self.nextRefresh)
       del self.selectedList[:]
       positionMapping=[]
       filter(lambda (i, j): positionMapping.append(j), self.currentDisplay)
       for j in map(lambda x: positionMapping[int(x)], self.joblist.curselection() ):
           print 'Adding jobId:%d to selectedList' % (j.jobId,)
           self.selectedList.append(j)
       self.auth(self.selectedList)
       self.nextRefresh = self.after_idle(self.refresh)


   def refresh(self, event=None):
       self.after_cancel(self.nextRefresh)
       self.jq.refresh()
       displayJobs = self.jq.getClaimedJobs(self.loggedInUsername)
       if displayJobs != self.currentDisplay:
          self.joblist.delete(0,len(self.jobs) )
          if displayJobs is not None:
             for (jobId, job) in displayJobs:
                 self.joblist.insert(self.joblist.size(), job)
          self.joblist.update_idletasks()
          self.currentDisplay = displayJobs
       self.nextRefresh = self.after(6000, self.refresh)


class RemoteFrame(Frame):

   def __init__(self, selectedList, username, cloudAdapter,
                 conn=None, authHandler=None, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.jq = jobqueue
       self.pack(expand=YES, fill=BOTH)
       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s %6s' % ( 'Id', 'User', 'Client', 'Title', 'Sheets'), font='TkFixedFont' )
       self.jobHeader.pack(expand=YES, fill=X, anchor=N)
       self.joblist = Listbox(master=self, font='TkFixedFont', height=40, width=60)
       self.joblist.pack(expand=YES, fill=BOTH, anchor=N)
       self.selectedList = selectedList
       self.auth=authHandler
       if conn is None:
          self.conn = cups.Connection()
       else:
          self.conn = conn
       self.jobs = dict()
       self.currentDisplay = []
       self.loggedInUsername=username
       self.jq.refresh()
       self.nextRefresh = self.after_idle(self.refresh)
       self.joblist.bind('<Return>', self.handleAuth, add=True)
       self.unbind_all('<Key-Tab>')
       self.unbind_all('<Shift-Key-Tab>')
       switchToRemote = 'tk::TabToWindow [tk_focusNext %s]' % (self._w,)
       self.bind_all('<Key-Right>', switchToRemote, add=False)

   def handleAuth(self, event=None):

       self.after_cancel(self.nextRefresh)
       del self.selectedList[:]
       positionMapping=[]
       filter(lambda (i, j): positionMapping.append(j), self.currentDisplay)
       for j in map(lambda x: positionMapping[int(x)], self.joblist.curselection() ):
           print 'Adding jobId:%d to selectedList' % (j.jobId,)
           self.selectedList.append(j)
       self.auth(self.selectedList)
       self.nextRefresh = self.after_idle(self.refresh)


   def refresh(self, event=None):
       self.after_cancel(self.nextRefresh)
       displayJobs = self.cloudAdapter.getIndex(self.loggedInUsername)
       if displayJobs != self.currentDisplay:
          self.joblist.delete(0,len(self.jobs) )
          if displayJobs is not None:
             for (jobId, job) in displayJobs:
                 self.joblist.insert(self.joblist.size(), job)
          self.joblist.update_idletasks()
          self.currentDisplay = displayJobs
       self.nextRefresh = self.after(6000, self.refresh)


class UnclaimedFrame(Frame):
   def __init__(self, selectedList, username, jobqueue,
                 conn=None, authHandler=None, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.jq = jobqueue
       self.pack(expand=YES, fill=BOTH)
       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s %6s' % ( 'Id', 'User', 'Client', 'Title', 'Sheets'), font='TkFixedFont' )
       self.jobHeader.pack(expand=YES, fill=X, anchor=N)
       self.joblist = Listbox(master=self, height=60, width=60,font='TkFixedFont')
       self.joblist.pack(expand=YES, fill=X, anchor=N)
       self.selectedList = selectedList
       self.auth=authHandler
       if conn is None:
          self.conn = cups.Connection()
       else:
          self.conn = conn
       self.jobs = dict()
       self.currentDisplay = []
       self.loggedInUsername=username
       self.jq.refresh()
       self.nextRefresh = self.after_idle(self.refresh)
       self.joblist.bind('<Return>', self.handleAuth, add=True)

   def handleAuth(self, event=None):
       self.after_cancel(self.nextRefresh)
       del self.selectedList[:]
       positionMapping=[]
       filter(lambda (i, j): positionMapping.append(j), self.currentDisplay)
       for j in map(lambda x: positionMapping[int(x)], self.joblist.curselection() ):
           print 'Adding jobId:%d to selectedList' % (j.jobId,)
           self.selectedList.append(j)
       self.auth(self.selectedList)
       self.nextRefresh = self.after_idle(self.refresh)


   def refresh(self, event=None):
       self.after_cancel(self.nextRefresh)
       self.jq.refresh()
       displayJobs = self.jq.getUnclaimedJobs()
       if displayJobs != self.currentDisplay:
          self.joblist.delete(0,len(self.jobs) )
          if displayJobs is not None:
             for (jobId, job) in displayJobs:
                 self.joblist.insert(self.joblist.size(), job)
          self.joblist.update_idletasks()
          self.currentDisplay = displayJobs
       self.nextRefresh = self.after(6000, self.refresh)

