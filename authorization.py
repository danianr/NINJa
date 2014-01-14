from pageserverreq import PageServerRequest
import random

class AuthorizationRequest(PageServerRequest):

    def __init__(self, username, printer, pages):
       PageServerRequest.__init__(self)
       self.username = username
       self.printer = printer
       self.pages = pages
       self.reqid = random.randint(4096, 16**5 - 1)
       self.status = "unsent"

    def getURL(self):
       return '%s/query/%s/%s/%x/%d' % (self.baseURL, self.printer, self.username, self.reqid, self.pages)
