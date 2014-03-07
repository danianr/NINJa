from Tkinter import *
import kerberos

class AuthDialog(Toplevel):
   def __init__(self, callback, username=None, readonlyUser=False, master=None, **cnf):
       apply(Toplevel.__init__, (self, master), cnf)
       self.authenticated = False
       self.authenticationSubmitted = False
       self.callback = callback
       self.username = StringVar(value=username)
       self.password = StringVar()
       self.message = StringVar()
       self.authTriesRemaining = 3
       if readonlyUser is False:
          self.message.set('Please enter your UNI and password below')
          usernameState = 'normal'
       else:
          self.message.set('Please enter your password below')
          usernameState = 'readonly'

       self.text=Label(self, textvar=self.message)
       self.text.pack(anchor=N, expand=YES, fill=X)
       userbox = Frame(self)
       userbox.pack()
       passbox = Frame(self)
       passbox.pack()
       Label(userbox, text='Username:').pack(side=LEFT, anchor=E)
       Label(passbox, text='Password:').pack(side=LEFT, anchor=E)
        
       self.usernameEntry = Entry(userbox, textvar=self.username, state=usernameState)
       self.passwordEntry = Entry(passbox, textvar=self.password, show='*')
       self.usernameEntry.pack(side=RIGHT, fill=X)
       self.passwordEntry.pack(side=RIGHT, fill=X)
       self.focusmodel(model="active")
       self.focus_set()
       self.tkraise()
       self.event_add('<<CloseDialog>>', '<Key-Escape>')
       self.usernameEntry.bind('<Key-Return>', lambda e: self.passwordEntry.focus_set()  )
       self.passwordEntry.bind('<Key-Return>', self.authenticateKerberos )
       self.bind('<<CloseDialog>>', self.cleanup )

   def authenticateKerberos(self, event):
       try:
            self.authenticated = kerberos.checkPassword(self.username.get(), self.password.get(), \
				                          'krbtgt/CC.COLUMBIA.EDU', 'CC.COLUMBIA.EDU')
       except kerberos.KrbError as ae:
            print ae
            self.authTriesRemaining -= 1
            self.message.set('Password incorrect, try again.')
            self.text['fg'] = 'red'

       if self.authenticated:
          self.text['fg'] = 'darkgreen'
          self.message.set('Password accepted')
          print 'User %s authenticated successfully' % ( self.username.get(), )
          
          self.after(600, self.event_generate, '<<CloseDialog>>')
       else:
          print 'Authentication unsuccessful'
          print 'authTriesRemaining: %d' % self.authTriesRemaining
	  if self.authTriesRemaining < 1:
             self.event_generate('<<CloseDialog>>')

   def cleanup(self, event):
       self.callback(self.username.get(), self.authenticated)
       self.destroy()
