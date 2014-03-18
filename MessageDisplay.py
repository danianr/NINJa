import xml.etree.ElementTree as ET
import time
import base64
from collections import deque
import Tkinter



class Bulletin(object):
   def __init__(self, id, message, begins, ends, precedence, imageURL=None):
       now = time.time()
       self.messageid = id

       #time fix for broken server response
       if int(begins) < 100000000:
          self.begins = int(begins) * 1000
       else:
          self.begins = int(begins)

       if int(ends)  < 100000000:
          self.ends = int(ends) * 1000
       else:
          self.ends   = ends

       self.precedence = precedence
       self.imageURL = imageURL
       self.message = message
       self.widget = None
       if now > begins:
          self.diplay = True
       else:
          self.display = False
       if now > ends:
          self.expired = True
       else:
          self.expired = False

class MessageDisplay(object):

   def __init__(self, population='Morningside', errorcb=None):
       self.population     = population
       self.messageFrame   = None
       self.errorcb        = errorcb
       self.bulletins      = dict()
       self.queue          = deque()
       self.message        = Tkinter.StringVar()
       self.defaultMessage = 'Welcome to the NINJa Printing System'
       self.message.set(self.defaultMessage)
       

   def registerMessageFrame(self, messageFrame):
       self.messageFrame = messageFrame
       self.messageFrame.bind_all('<<Bulletin>>', self.update)
       self.displayLabel = Tkinter.Label(textvar=self.message, master=messageFrame)
       self.displayLabel.pack()
       self.messageFrame.pack()

   def registerErrorCallback(self, errorcb):
       self.errorcb = errorcb

   def update(self, event=None):
       now = time.time()
       if self.bulletins.has_key('quota'):
          qb = self.bulletins['quota']
          if  qb.ends > now:
              self.message.set(qb.message)
              return

       if len(self.queue) > 0:
          processQueue = True
          while processQueue:
             b = self.queue.popleft()
             if b.ends <= now:
                self.bulletins.remove(b)
                if len(self.queue) == 0:
                   processQueue = False
                   self.message.set(self.defaultMessage)
             else:
                self.message.set(b.message)
                processQueue = False
       
       self.queue.extend(filter( lambda x: (x.begins < now and x.ends > now), self.bulletins.values()))
       

   def bulletin(self, xml, element):
       bulletinBoard = xml.find(element).getchildren()
       for b in bulletinBoard:
          id = b.attrib['id']
          precedence = b.attrib['precedence']
          begins = b.attrib['begins']
          ends = b.attrib['ends']
          try:
            imageURL = b.attrib['imageURL']
          except:
            imageURL = None
          text = b.text
          msg = Bulletin(id, text, begins, ends, precedence, imageURL)
          if not self.bulletins.has_key(msg.messageid):
             self.bulletins[msg.messageid] = msg
          

   def quota(self, xml, element, insufficientQuota=False):
       quotas = xml.find(element)
       dollars     = quotas.find('dollars')
       aggregated  = quotas.find('aggregatedQuotas')
       morningside = quotas.find('AcICBlackAndWhite')
       socialwork  = quotas.find('SSWBlackAndWhite')
       barnard     = quotas.find('BCBlackAndWhite')

       if population == 'Morningside':
          weekly     = morningside.find('weekly').attrib['remaining']
          semesterly = morningside.find('semesterly').attrib['remaining']
          amount     = dollars.attrib['amount']
          paidavail  = dollars.find('AcISBlackAndWhite').attrib['available']

       elif population == 'Social Work':
          weekly     = socialwork.find('weekly').attrib['remaining']
          semesterly = socialwork.find('semesterly').attrib['remaining']
          amount     = dollars.attrib['amount']
          paidavail  = dollars.find('SSWBlackAndWhite').attrib['available']

       elif population == 'Barnard':
          weekly     = barnard.find('weekly').attrib['remaining']
          semesterly = barnard.find('semesterly').attrib['remaining']
          amount     = barnard.attrib['amount']
          paidavail  = barnard.find('BCBlackAndWhite').attrib['available']

       elif population == 'Teachers College':
          weekly     = morningside.find('weekly').attrib['remaining']
          semesterly = morningside.find('semesterly').attrib['remaining']
          amount     = morningside.attrib['amount']
          paidavail  = morningside.find('AcISBlackAndWhite').attrib['available']

       else:
          print 'Unknown population [%s]\n' % (population,)
          return

       ts='Quota Information for %s Printers\n' % (self.Population,)
       qs = 'Weekly Quota Remaining:   %4d sheets\nSemester Quota Remaining: %4d sheets\n' \
           % ( int(weekly), int(semesterly) ) 
       ds = 'Paid Sheets Available:    %d\n\nPrinting Dollar Balance: %s\n' \
              % ( int(paidamount), int(amount) )
       self.bulletins.append(Bulletin('quota', -1, ts + qs + ds, int(time.time()) + 300, 1))
       if insufficientQuota and self.errorcb is not None:
          self.errorcb('Insufficent Quota')
          
