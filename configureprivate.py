import cups
import os
import re
import socket
import sys
import telnetlib
import time



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


def configure_private(conn, privatename, printername):

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
    elif model.group(2) == 'LaserJet M806':
         conn.addPrinter(privatename, filename='hp-laserjet_m806-ps.ppd', device='socket://%s' % (printername,) )
         print 'Added a LaserJet M806 for ', privatename
    else:
         conn.addPrinter(privatename, device='socket://%s' % (printername,) )
         print 'Added a generic JetDirect socket printer for ', privatename

    try:
      return conn.getDests()[(privatename, None)]
    except:
      return None
