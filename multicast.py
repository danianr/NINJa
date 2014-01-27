import socket
import thread
import re

class MulticastMember(object):

   def __init__(self, addr, port, ttl, unipattern):

      self.unipattern = unipattern
      self.uuidpattern = re.compile('urn:uuid:(.{8})-(.{4})-(.{4})-(.{4})-(.{12})')
      self.inet4pattern = re.compile('(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})')
      self.addr = addr
      self.port = port
      self.ttl = ttl
      self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      try:
         self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
      except AttributeError:
         pass
      self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, self.ttl)
      self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)

      self.sock.bind(('', port))

      intf = socket.gethostbyname(socket.gethostname())
      self.sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF,
                                                       socket.inet_aton(intf))
      self.sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
                              socket.inet_aton(addr) + socket.inet_aton(intf))
      print "using interface %s for multicast group %s\n" % (intf, addr)


   def advertise(self,job):

      if self.unipattern.match(job.username):
          m = self.uuidpattern.match(job.uuid)
          uuid = '%s%s%s%s%s' % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))

          src = socket.gethostbyname(job.hostname)
          m = self.inet4pattern.match(src)
          src = '%.3d.%.3d.%.3d.%.3d' % (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))

          dst = socket.gethostbyname(socket.gethostname())
          m = self.inet4pattern.match(dst)
          dst = '%.3d.%.3d.%.3d.%.3d' % (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))

          data = '%32s%128s%.20lu%.5u%1u%15s%15s%-15s%-63s\n' % ( uuid, job.sha512, job.creation, job.pages, 
                                job.duplex, src, dst, job.username, job.title[:63] )
          print data
          s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
          s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.ttl)
          s.bind(('', socket.INADDR_ANY))
          s.sendto(data, (self.addr, self.port))
          s.close()
      else:
          print 'ignoring job from user:%s\n' % job.username
