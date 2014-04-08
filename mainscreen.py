from Tkinter import *
from os import popen
from jobqueue import *
from remoteframe import RemoteFrame
import time
import cups
import ttk



class MainScreen(Frame):
   def __init__(self, username, jobqueue, cloudAdapter, conn,
                  authHandler,  messageDisplay, logoutCb, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.pack(expand=YES, fill=BOTH)
       self.tk  = master
       self.notebook = ttk.Notebook(master=self)

       self.totalWidth = 1180
       self.totalHeight = 940
       self.rightWidth  = 560
       self.slideRatio  = 0.80

       self.instructions = StringVar()
       self.instructions.set('Left arrow selects Local jobs, Right arrow selects remote jobs, Enter prints')
       self.messageDisplay = messageDisplay
       self.instrbar = Label(textvar=self.instructions, master=self)
       self.instrbar.pack(side=BOTTOM, fill=X, expand=N)
       self.hpane = ttk.PanedWindow(orient=HORIZONTAL, width=self.totalWidth, height=self.totalHeight)
       self.vpane = ttk.PanedWindow(orient=VERTICAL,width=self.rightWidth, height=self.totalHeight)
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
       self.notebook.tab(0, text=username + "'s jobs")
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

       self.unbind_all('<Key-Tab>')
       self.unbind_all('<Shift-Key-Tab>')
       self.event_add('<<SwitchView>>', '<Key-Tab>')
       self.bind_all('<<SwitchView>>', self.switchView )

       self.bind_all('<<LocalJobs>>', self.switchLocal )
       self.bind_all('<<RemoteJobs>>', self.switchRemote )
       self.event_add('<<Logout>>', '<Key-Escape>')
       self.bind_all('<<Logout>>', self.logout )
       self.jobWidget =  ( self.local.joblist, self.unclaimed.joblist )

   def switchLocal(self, event=None):
       self.hpane.sashpos(0, newpos=int(self.totalWidth * self.slideRatio))
       self.remote.joblist['background'] = '#cdc9c5'
       self.local.joblist['background']  = 'white'
       self.local.joblist.focus_set()

   def switchRemote(self, event=None):
       self.hpane.sashpos(0, newpos=int(self.totalWidth * (1 - self.slideRatio)) )
       self.local.joblist['background'] = '#cdc9c5'
       self.remote.joblist['background'] = 'white'
       self.remote.joblist.focus_set()

   def resetView(self):
       self.hpane.sashpos(0,newpos=self.totalWidth - self.rightWidth)
       self.remote.joblist['background'] = 'white'
       self.local.joblist['background'] = 'white'
       self.local.joblist.focus_set()

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
       if nexttab == 0:
          self.resetView()

   def takefocus(self):
       if self.local is not None and self.local.joblist is not None:
             self.local.joblist.focus_set()


   def setInstructions(self, instructions):
       self.instrbar.set(instructions)

   def getMessageDisplay(self):
       return self.mdisplay

   def logout(self, e):
       self.unbind_all('<<SwitchView>>')
       self.unbind_all('<<Logout>>')
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
       self.joblist = Listbox(master=self, height=60, width=60,font='TkFixedFont',background='white')
       self.joblist.pack(expand=YES, fill=BOTH, anchor=N)

       # Key Bindings
       self.joblist.bind('<Return>', self.handleAuth, add=True)
       self.event_add('<<LocalJobs>>', '<Key-Left>')
       self.jobMapping = None
       self.nextRefresh = self.after_idle(self.refresh)


   def handleAuth(self, event=None):
       self.after_cancel(self.nextRefresh)
       selectedList = self.jobMapping.map(self.joblist.curselection())
       self.auth(selectedList, self.errorcb, self.loggedInUsername)
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
       self.joblist = Listbox(master=self, height=60, width=60,font='TkFixedFont',background='white')
       self.joblist.pack(expand=YES, fill=X, anchor=N)
       self.joblist.bind('<Return>', self.handleAuth, add=True)

       self.jobMapping  = None
       self.nextRefresh = self.after_idle(self.refresh)


   def handleAuth(self, event=None):
       self.after_cancel(self.nextRefresh)
       selectedList = self.jobMapping.map(self.joblist.curselection())
       self.auth(selectedList, self.errorcb, self.loggedInUsername)
       self.event_generate('<<SwitchView>>')
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
