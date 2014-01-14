import Tkinter
from controller import Controller

tk = Tkinter.Tk()

def error_message(errortext):
   tl = Tkinter.Toplevel()
   fr = Tkinter.Frame(master=tl)
   message = Tkinter.Label(text=errortext, master=fr)
   message.pack(side=TOP)
   dismiss = Tkinter.Button(text="Close", command=tl.destroy, master=fr)
   dismiss.pack(side=BOTTOM, anchor=E)
   fr.pack()

if __name__ == '__main__':

   controller = Controller('watson8-printer_atg_columbia_edu', 'watson8-ninja.atg.columbia.edu',
                            public='public', tk=tk)
   controller.start()
