import xml.etree.ElementTree as ET
import time
import base64
from collections import deque
import Tkinter



class Bulletin(object):
   def __init__(self, id, message, begins, ends, precedence, imageURL=None):
       now = time.time()
       self.messageid = id
       self.sig = int(base64.b64_decode(id).encode('hex'), 16)
       self.begins = begins
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


   def __eq__(x, y):
        return x.messageid == y.messageid

   def __ne__(x, y):
        return x.messageid != y.messageid

   def __hash__(self):
        if self.id == 'quota':
           return -1
        else:
           return self.sig % 2147483647
           
    # Lower precedence is a higher priority
    # Reverse sorting should be used
   def __cmp__(x, y):
        return cmp(y.precedence, x.precedence)

   def __gt__(x, y):
        return y.precedence > x.precedence

   def __ge__(x, y):
        return x.precedence >= x.precedence

   def __lt__(x, y):
        return y.precedence < x.precedence

   def __le__(x, y):
        return y.precedence <= x.precedence


class MessageDisplay(object):

   def __init__(self, population='Morningside', errorcb=None):
       self.population     = population
       self.messageFrame   = None
       self.errorcb        = errorcb
       self.bulletins      = set()
       self.queue          = deque()
       self.message        = Tkinter.StringVar()
       self.defaultMessage = 'Welcome to the NINJa Printing System'
       

   def registerMessageFrame(self, messageFrame):
       self.messageFrame = messageFrame
       self.displayLabel = Label(textvar=self.message, master=self.messageFrame)
       self.displayLabel.pack()
       self.messageFrame.pack()


   def update(self):
       if self.messageFrame is None:
          return

       now = time.time()
       qb = filter( lambda x: (x.messageid == 'quota'), self.bulletins)
       if len(qb) > 0 and qb[0].ends > now:
          self.message.set(qb[0].message)
          return

       if len(self.queue):
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
       
       self.queue.extend(filter( lambda x: (x.begins < now and x.ends > now), self.bulletins))
       

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
          self.bulletins.add(Bulletin(id, text, begins, ends, precedence, imageURL))
          


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
          
