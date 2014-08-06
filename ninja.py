import Tkinter
import ttk
import cups
import httplib
import os
import re
import socket
import sys
import telnetlib
import time
from controller import Controller



def read_gridlist():
    url = '/~dr2481/gridlist.txt'
    http = httplib.HTTPConnection('www.columbia.edu')
    http.request("GET", url)
    resp = http.getresponse()
    content = resp.read()
    return filter(lambda s:  len(s) > 0 and s[0] != '#', content.split('\n'))


def name_tuple():
   # Determine the name of the associated printer by replacing the "ninja" substring
   # of the current hostname with "printer".  Validate this hostname by performing
   # a gethostbyname and proceed to use the canonical hostname for the appsocket:
   # interface of the private destination.

   ninjaname = socket.getfqdn()
   print >> sys.stderr, time.time(), "ninja:", ninjaname 
   printername = ninjaname.replace('ninja', 'printer')
   print >> sys.stderr, time.time(), "printername:", printername
   printername = (socket.gethostbyname_ex(printername))[0]
   print >> sys.stderr, time.time(), "printername:", printername
   privatename = printername.replace('.','_')
   print >> sys.stderr, time.time(), "privatequeue:", privatename
   return (ninjaname, printername, privatename)


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
       modelsRE = [ re.compile('(?i).*"(HP) (LaserJet P4515)"'), re.compile('(?i).*"(hp) (LaserJet 9050)"'),
                    re.compile('(?i).*"(HP) (LaserJet M806)"') ]
       pjlcmd = '\033%-12345X@PJL\n@PJL INFO ID\n'
       pjl = telnetlib.Telnet(printername, 9100, 7)
       pjl.write(pjlcmd)
       time.sleep(10)
       (n, model, string)  = pjl.expect(modelsRE)
       pjl.close()
       if model.group(2) == 'LaserJet P4515': 
         conn.addPrinter(privatename, ppdname='drv:///hpcups.drv/hp-laserjet_p4515x.ppd',
                                      device='socket://%s' % (printername,) )
         print 'Added a LaserJet P4515x for ', privatename
       elif model.group(2) == 'LaserJet 9050':
         conn.addPrinter(privatename, ppdname='drv:///hpcups.drv/hp-laserjet_9050-pcl3.ppd',
                                      device='socket://%s' % (printername,) )
         print 'Added a LaserJet 9050 for ', privatename
       elif model.group(2) == 'HP LaserJet M806':
         conn.addPrinter(privatename, filename='hp-laserjet_m806-ps.ppd', device='socket://%s' % (printername,) )
         print 'Added a LaserJet M806 for ', privatename
       else:
         conn.addPrinter(privatename, device='socket://%s' % (printername,) )
         print 'Added a generic JetDirect socket printer for ', privatename

   
   gridlist = read_gridlist()
   print >> sys.stderr, time.time(), "gridlist: ",repr(gridlist)
   controller = Controller(private=privatename, authname=ninjaname, public='public', gridlist=gridlist, tk=tk)
   print >> sys.stderr, time.time(), "Controller initialized"

   controller.downloadBulletins('https://wwwapp.cc.columbia.edu/atg/PageServer/bulletin')
   print >> sys.stderr, time.time(), "Bulletins downloaded"
  
   controller.start()
