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

    # Regular expressions for identifying printer, printer-make-and-model
    # should be captured in the second group, with manufacturer in the first
    # group if possible

    modelsRE = [ re.compile('(?i).*"(hp) (LaserJet 9050)"'),
                 re.compile('(?i).*"(HP) (LaserJet P4515)"'),
                 re.compile('(?i).*"(HP) (LaserJet M806)"') ]

    ppdNameMap = [ 'postscript-hp:0/ppd/hplip/HP/hp-laserjet_9050-ps.ppd',
                   'drv:///hpijs.drv/hp-laserjet_p4515x-hpijs.ppd',
                   'hp-laserjet_m806-ps.ppd' ]
                   

    # Use the telnetlib module to submit a PJL INFO command directly
    # to the appsocket interface of the printer and select the appropriate
    # PPD based on which regular expression matches

    pjlcmd = '\033%-12345X@PJL\n@PJL INFO ID\n'
    pjl = telnetlib.Telnet(printername, 9100, 7)
    pjl.write(pjlcmd)
    time.sleep(10)
    (n, model, string)  = pjl.expect(modelsRE)
    pjl.close()

    if ppdNameMap[n].startswith('drv://') or ppdNameMap[n].startswith('postscript-hp:') :
        localPPD = cups.PPD(conn.getServerPPD(ppdNameMap[n]))
    else:
        localPPD = cups.PPD(ppdNameMap[n])
    
    if n == 0:
       localPPD.markOption('HPOption_2000_Sheet_Tray', 'True')
       localPPD.markOption('HPOption_Duplexer', 'True')
       localPPD.markOption('InstalledMemory', '384 - 512 MB')
       localPPD.markOption('HPOption_PaperPolicy', 'NearestSizeNoAdjust')
       localPPD.markOption('Duplex', 'DuplexNoTumble')
    else:
       localPPD.markOption('OptionDuplex', 'True')
       localPPD.markOption('Duplex', 'DuplexNoTumble')

    try:
       conn.addPrinter(privatename, ppd=localPPD, device='socket://%s' % (printername,))
       return conn.getDests()[(privatename, None)]
    except cups.IPPError:
       print >> sys.stderr, time.time(), "Could not add private queue:", privatename, " for ", printername
       return None
