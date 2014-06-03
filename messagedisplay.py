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
       self.populationMap  = { 'Morningside' : 'AcISBlackAndWhite',
                               'Social Work' : 'SSWBlackAndWhite',
                               'Barnard' : 'BCBlackAndWhite',
                               'Teachers College' : 'AcISBlackAndWhite',
                               'Dev' : 'AdminTest',
                               'Administrative' : 'AdminTest' }

   def registerMessageFrame(self, messageFrame):
       self.messageFrame = messageFrame
       if self.messageFrame is not None:
           self.messageFrame.bind_all('<<Bulletin>>', self.update)
           self.displayLabel = Tkinter.Label(textvar=self.message, master=messageFrame)
           self.displayLabel.pack()
           self.messageFrame.pack()

   def registerErrorCallback(self, errorcb):
       self.errorcb = errorcb

   def getInterlock(self):
       if self.messageFrame is None:
          return None
       else:
          interlock = self.messageFrame.getvar("PRINT_INTERLOCK")
          print 'interlock = %s\n' % (interlock,)
          return interlock

   def claimInterlock(self):
       if self.messageFrame is None:
          return
       else:
          print 'claiming interlock'
          self.messageFrame.setvar(name='PRINT_INTERLOCK', value='1')
          return

   def releaseInterlock(self):
       if self.messageFrame is None:
          return
       else:
          print 'releasing interlock'
          self.messageFrame.setvar(name='PRINT_INTERLOCK', value='0')
          return

   def waitInterlock(self):
       if self.messageFrame is None:
          return
       if self.messageFrame.getvar('PRINT_INTERLOCK') == '0':
          self.messageFrame.waitvar('PRINT_INTERLOCK')

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
                del self.bulletins[b]
                if len(self.queue) == 0:
                   processQueue = False
                   self.message.set(self.defaultMessage)
             else:
                self.message.set(b.message)
                processQueue = False
       
       self.queue.extend(filter( lambda x: (x.begins < now and x.ends > now), self.bulletins.values()))
       

   def bulletin(self, xml, element):
       top = xml.find(element)
       if top is None:
          return
       else:
          bulletinBoard = top.getchildren()

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
          

   def quota(self, xml, path, insufficientQuota=False):

       dollars     = xml.find(path + '/uni/dollars')
       aggregated  = xml.find(path + '/uni/aggregatedQuotas')

       tag = self.populationMap[self.population]

       if dollars is not None:
          amount    = dollars.attrib['amount']
          paidavail = dollars.find(tag).attrib['available']
       else:
          amount    = 0
          paidavail = 0

       weekly     = aggregated.find(tag + '/weekly').attrib['remaining']
       semesterly = aggregated.find(tag + '/semesterly').attrib['remaining']

       ts='Quota Information for %s Printers\n' % (self.population,)
       qs = 'Weekly Quota Remaining:   %4d sheets\nSemester Quota Remaining: %4d sheets\n' \
           % ( int(weekly), int(semesterly) ) 
       ds = 'Paid Sheets Available:    %d\n\nPrinting Dollar Balance: %s\n' \
              % ( int(paidavail), amount)
       self.bulletins['quota'] = Bulletin('quota', ts + qs + ds, 1, int(time.time()) + 300, 1)
       if insufficientQuota and self.errorcb is not None:
          self.errorcb('Insufficent Quota')


   def clearQuota(self, event=None):
       if self.bulletins.has_key('quota'):
           del self.bulletins['quota']
       self.update()
