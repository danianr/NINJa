from Tkinter import *
from ttk import *
from os import popen
from jobqueue import *
from remoteframe import RemoteFrame
import sys
import time
import cups



class MainScreen(Frame):
   def __init__(self, username, jobqueue, cloudAdapter, conn,
                  authHandler,  messageDisplay, logoutCb, maxsize=214783647, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.pack(expand=YES, fill=BOTH)
       self.tk  = master
       self.notebook = Notebook(master=self)

       # Manually set the initial autologout, afterwards use the resetAutologout function
       self.autologout = self.after(180000, self.logout)

       self.logo = PhotoImage(file="logo.gif")
       height = self['height'] - self.logo.height() - 30
       width = self['width']
       msgDsplyHeight = 200
       rightWidth  = 560
       paneHeight = height - 30

       print >> sys.stderr, time.time(), 'height:%d width: %d paneHeight:%d msgDsplyHeigh:%s rightWidth:%d' \
             % (height, width, paneHeight, msgDsplyHeight, rightWidth)

       self.instructions = StringVar()
       self.info = ('[Left] selects Local Jobs\t[Right] selects Cloud Jobs\n[Esc] Logout\n[Tab] Unclaimed Jobs     \t[Enter] Prints Selected Job',
              '[Tab] Return to Main Screen\n[Esc] Logout\n[Enter] Prints Selected Job without further prompting')
       self.instructions.set(self.info[0])
       self.messageDisplay = messageDisplay
       self.hpane = PanedWindow(orient=HORIZONTAL, width=width, height=height)
       self.vpane = PanedWindow(orient=VERTICAL,width=rightWidth - 10, height=height)
       self.mdisplay = Frame(width=rightWidth, height=msgDsplyHeight)
       self.messageDisplay.registerMessageFrame(self.mdisplay)
       self.messageDisplay.registerErrorCallback(self.errorCallback)
       self.popupMessage = StringVar()
       self.popupMessage.set('Please wait, your document is being printed')
       self.logoframe = Frame()
       self.logoframe['bg'] = 'white'
       Label(image=self.logo, bg='white', justify=LEFT).pack(in_=self.logoframe, side=LEFT, anchor=N, ipadx=80)
       Label(textvar=self.instructions, bg='white', fg='black', justify=LEFT).pack(in_=self.logoframe, side=RIGHT, anchor=N, ipadx=rightWidth/4, ipady=8)
       self.logoframe.pack(in_=self, side=TOP, fill=X, expand=Y)
       self.local = LocalFrame(username, jobqueue, conn, authHandler.authorizeJobs, self.errorCallback, self.resetAutologout, maxsize=maxsize,width=width - rightWidth, height=paneHeight)
       self.remote = RemoteFrame(username, jobqueue, cloudAdapter, conn, authHandler.authorizeJobs, self.errorCallback, self.resetAutologout, width=rightWidth - 10 , height=paneHeight - msgDsplyHeight - 10)
       self.hpane.add(self.local)
       self.vpane.add(self.remote)
       self.vpane.add(self.mdisplay)
       self.hpane.add(self.vpane)
       self.notebook.add(self.hpane)
       self.notebook.tab(0, text=username + "'s jobs")
       self.unclaimed = UnclaimedFrame(username, jobqueue, conn, authHandler.authorizeJobs, self.errorCallback, self.resetAutologout, height=height, width=width)
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
       self.event_add('<<SwitchView>>', '<Shift-Key-Tab>')
       self.event_add('<<CancelJob>>',  '<Key-F5>')
       self.event_add('<<Logout>>',     '<Key-Escape>')
      
       self.bind_all('<<Printing>>',   self.popupStatus) 
       self.bind_all('<<SwitchView>>', self.switchView )

       def localfocus(event):
          try:
             self.local.joblist.focus_set()
          except:
             (exc_type, exc_value, exc_traceback) = sys.exc_info()
             print >> sys.stderr, time.time(), 'Caught during localfocus', exc_type, exc_value, event.__dict__
    
       self.bind_all('<<LocalJobs>>',  localfocus )


       def remotefocus(event):
          try:
             self.remote.joblist.focus_set()
          except:
             (exc_type, exc_value, exc_traceback) = sys.exc_info()
             print >> sys.stderr, time.time(), 'Caught during remotefocus', exc_type, exc_value, event.__dict__

       self.bind_all('<<RemoteJobs>>', remotefocus )


       self.bind_all('<<Logout>>',     self.logout )
       self.bind_all('<<CancelJob>>',  authHandler.cancelCurrentJob )

       self.jobWidget =  ( self.local.joblist, self.unclaimed.joblist )
       self.update_idletasks()



   def errorCallback(self, message):
       self.popupMessage.set(message)
       self.tk.update_idletasks()
       self.after(6000, self.event_generate('<<Finished>>'))

   def popupStatus(self, event=None):
       print 'displaying popup status message'
       popup = Toplevel(master=self.tk, width=800, height=230)
       def closePopup(event):
           print 'closing popup window on event:', repr(event)
           popup.destroy()

       self.bind_all('<<Finished>>', closePopup)
       pulabel = Label(textvariable=self.popupMessage, master=popup, font='-*-helvetica-medium-r-normal-*-34-*-*-*-*-*-iso8859-1')
       pulabel.pack()
       

   def switchView(self, e):
       if isinstance(e.widget, Listbox):
          e.widget.selection_clear(0, 'end')
       current = self.notebook.select()
       nexttab = ( self.notebook.index(current) + 1 ) % self.notebook.index('end')
       self.instructions.set(self.info[nexttab])
       self.notebook.select(nexttab)
       self.jobWidget[nexttab].focus_set()
       if isinstance(self.jobWidget[nexttab], Listbox) and self.jobWidget[nexttab].size() > 0:
          self.jobWidget[nexttab].selection_set(0)
       else:
          print >> sys.stderr, time.time(), 'ELSE isinstance(%s) and jobWidget[%d].size(%d)\n' % ( isinstance(self.jobWidget[nexttab], Listbox), nexttab, self.jobWidget[nexttab].size() )

   def wm_title(self, title):
       self.tk.wm_title(title)

   def getMessageDisplay(self):
       return self.mdisplay

   def resetAutologout(self, inactivity):
       print "resetting auto logout to ", inactivity
       if self.autologout is not None:
          print "self.autologout was previously set"
          self.after_cancel(self.autologout)
          self.autologout = None
       self.autologout = self.after(inactivity * 1000, self.logout)

   def logout(self, e=None):
       if self.autologout is not None:
          self.after_cancel(self.autologout)
          self.autologout = None
       if self.getvar('PRINT_INTERLOCK') == '1':
          self.resetAutologout(45)
          return
       self.event_generate('<<Finished>>')
       self.unbind_all('<<LocalJobs>>')
       self.unbind_all('<<RemoteJobs>>')
       self.unbind_all('<<SwitchView>>')
       self.unbind_all('<<Logout>>')
       self.unclaimed.destroy()
       self.vpane.destroy()
       self.hpane.destroy()
       self.notebook.destroy()
       self.remote.destroy()
       self.local.destroy()
       self.logoframe.destroy()
       self.logoutCb()


class LocalFrame(Frame):
   def __init__(self, username, jobqueue, conn, authHandler, errorcb, resetAutologout, master=None, maxsize=2147483647, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.loggedInUsername = username
       self.jq      = jobqueue
       self.conn    = conn
       self.auth    = authHandler
       self.errorcb = errorcb
       self.maxsize = maxsize

       self.resetAutologout = resetAutologout
       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s   %6s' % \
                             ( 'Id', 'User', 'Printed From', 'Title', 'Sheets'), font='TkFixedFont',
                             padx='4', anchor='sw' )
       self.jobHeader.place(in_=self,x=0, y=30, anchor='sw', width=self['width'], height=30)
       self.joblist = Listbox(master=self, font='TkFixedFont',background='white',
                selectforeground='white', selectbackground='#003373', highlightthickness='3', highlightcolor='#75AADB')
       self.joblist.place(in_=self, x=0, y=30, width=self['width'], height=self['height'] - 30, anchor='nw')
       self.pack()

       # Key Bindings
       self.joblist.bind('<Return>', self.handleAuth, add=True)
       self.event_add('<<LocalJobs>>', '<Key-Left>')
       self.jobMapping = None
       self.nextRefresh = self.after_idle(self.refresh)


   def handleAuth(self, event=None):
       if self.joblist.size == 0 or len(self.joblist.curselection()) == 0:
          return
       if self.getvar('PRINT_INTERLOCK') == '1':
          return
       self.event_generate('<<Printing>>')
       self.after_cancel(self.nextRefresh)
       selectedList = self.jobMapping.map(self.joblist.curselection())
       toobig = filter(lambda j: (j.size > self.maxsize), selectedList)
       if len(toobig) > 0:
          for job in toobig:
             print >> sys.stderr, time.time(), 'Canceling job:%d due to size %d\n' % (job.jobId, job.size)
             self.conn.cancelJob(job.jobId)

          self.jobMapping.setDirty()
          self.refresh()
          for job in toobig:
             if job.error is None:
                self.errorcb('Unable to print job, too large')
             else:
                self.errorcb(job.error)
          # errorcb is terminal, but just to make this explicit
          return
       self.auth(selectedList, self.errorcb, self.loggedInUsername)
       self.resetAutologout(45)
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
   def __init__(self, username, jobqueue, conn, authHandler, errorcb, resetAutologout, master=None, **cnf):
       apply(Frame.__init__, (self, master), cnf)
       self.loggedInUsername = username
       self.jq               = jobqueue
       self.conn             = conn
       self.auth             = authHandler
       self.errorcb          = errorcb
       self.resetAutologout  = resetAutologout

       
       self.jobHeader = Label(self, text='%4s  %-12s %-18s %-48s   %6s' % \
                             ( 'Id', 'User', 'Client', 'Title', 'Sheets'), padx='4', anchor='sw', font='TkFixedFont' )
       self.jobHeader.place(in_=master, x=0, y=30, width=self['width'], height=30,anchor='sw')
       self.joblist = Listbox(master=self, font='TkFixedFont',background='white', highlightthickness='3',
                          selectbackground='#003373', selectforeground='white', highlightcolor='#75AADB')
       self.joblist.place(in_=master, x=0, y=30, width=self['width'] - 4, height=self['height'] - 30, anchor='nw', bordermode="outside")
       self.joblist.bind('<Return>', self.handleAuth, add=True)
       self.pack()
       self.jobMapping  = None
       self.nextRefresh = self.after_idle(self.refresh)


   def handleAuth(self, event=None):
       if self.joblist.size == 0 or len(self.joblist.curselection()) == 0:
          return
       if self.getvar('PRINT_INTERLOCK') == '1':
          return
       self.event_generate('<<Printing>>')
       self.after_cancel(self.nextRefresh)
       selectedList = self.jobMapping.map(self.joblist.curselection())
       self.auth(selectedList, self.errorcb, self.loggedInUsername)
       self.event_generate('<<SwitchView>>')
       self.resetAutologout(45)
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
