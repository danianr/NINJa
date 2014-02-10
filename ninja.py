import Tkinter
from controller import Controller


if __name__ == '__main__':


   # Any queue / destination / access control setup should take place here;
   # Obtain a cups.Connection object from the Controller for consistency

   controller = Controller('watson8-printer_atg_columbia_edu', 'watson8-ninja.atg.columbia.edu')
   controller.start()
