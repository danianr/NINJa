import Tkinter
import ttk
import cups
import httplib
import re
import socket
import sys
import time
from configureprivate import name_tuple, configure_private
from controller import Controller



def read_gridlist():
    url = '/~dr2481/gridlist.txt'
    http = httplib.HTTPConnection('www.columbia.edu')
    http.request("GET", url)
    resp = http.getresponse()
    content = resp.read()
    return filter(lambda s:  len(s) > 0 and s[0] != '#', content.split('\n'))


if __name__ == '__main__':

   # Color Palette setup
   tk = Tkinter.Tk()
   tk.tk_setPalette(background='#ACCCE6', foreground='#003373', selectForeground='#003373',
                    selectBackground='white', selectColor='#75AADB', troughColor='#75AADB')

   style = ttk.Style()
   style.configure('TNotebook',background='#ACCCE6', foreground='#003373' ) 
   style.configure('PanedWindow',background='#75AADB', foreground='#003373' ) 
   style.configure('PanedWindow',separator='pink', fill='orange', vseparator='purple', hseparator='green' ) 
   

   style.map('TNotebook.Tab', background=[('selected','#75AADB'), ('!active', '#ACCCE6')],
                              foreground=[('selected','white'), ('!disabled', '#003373')],
                              font=[('!active', '-adobe-helvetica-medium-r-normal--14-140-75-75-p-77-iso8859-1')])

   # Any queue / destination / access control setup should take place here;
   # Use a separate cups.Connection from the controller as the initializer
   # relies on the public/private queues being previously setup close the
   # cups connection prior to starting the Controller to avoid multiple
   # points of resource access

   conn = cups.Connection()
   cupsDestinations = conn.getDests()

   # Add a public queue with the file:/dev/null device as a holding destination
   if ('public', None) not in cupsDestinations:
      conn.addPrinter('public')

   # Add a remote queue with the file:/dev/null device to act as a processing queue
   # for cloud jobs which are being copied into the local queue prior to printing,
   # this will let us hide the job from the locally displayed jobs without having
   # to reimplement identical authorization/accounting logic for the release of
   # cloud print jobs
   if ('remote', None) not in cupsDestinations:
      conn.addPrinter('remote')
   conn.disablePrinter('remote')
   conn.acceptJobs('remote')

   ninjaname   = None
   printername = None
   privatename = None
   for attempt in range(10):
      try: 
         (ninjaname, printername, privatename) = name_tuple()
         break
      except:
         time.sleep(2)

   if (ninjaname is None or printername is None or privatename is None):
       print >> sys.stderr, "Unable to determine DNS names needed to continue"
       exit(2)

   if (privatename, None) not in cupsDestinations:
       dest = configure_private(conn, privatename, printername)
       print >> sys.stderr, time.time(), "Added private queue ", repr(dest.options)

   
   gridlist = read_gridlist()
   print >> sys.stderr, time.time(), "gridlist: ",repr(gridlist)
   controller = Controller(private=privatename, authname=ninjaname, public='public', gridlist=gridlist, tk=tk)
   print >> sys.stderr, time.time(), "Controller initialized"

   controller.downloadBulletins('https://wwwapp.cc.columbia.edu/atg/PageServer/bulletin')
   print >> sys.stderr, time.time(), "Bulletins downloaded"
  
   controller.start()
