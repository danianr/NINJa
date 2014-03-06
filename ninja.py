import Tkinter
import cups
import os
import socket
from controller import Controller


if __name__ == '__main__':


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

   # Determine the name of the associated printer by replacing the "ninja" substring
   # of the current hostname with "printer".  Validate this hostname by performing
   # a gethostbyname and proceed to use the canonical hostname for the appsocket:
   # interface of the private destination.
   ninjaname = (os.uname())[1]
   ninjaname = (socket.gethostbyname_ex(ninjaname))[0]
   printername = ninjaname.replace('ninja', 'printer')
   privatename = printername.replace('.','_')
   printername = (socket.gethostbyname_ex(printername))[0]


   if (privatename, None) not in cupsDestinations:
       modelsRE = [ re.compile('(?i).*"(HP) (LaserJet P4515)"'), re.compile('(?i).*"(hp) (LaserJet 9050)"') ]
       drivermap = dict()
       pjlcmd = '\033%-12345X@PJL\n@PJL INFO ID\n'
       pjl = telnetlib.Telnet(printername, 9100, 7)
       pjl.write(pjlcmd)
       time.sleep(10)
       (n, model, string)  = pjl.expect(modelsRE)
       print model.group(1), model.group(2)
       pjl.close()

      conn.addPrinter(privatename, device='socket://%s' % (printername,) )

   controller = Controller(privatename, ninjaname)
   controller.start()
