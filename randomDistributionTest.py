import random
import sys


testSizes = [ 5, 13, 23, 37, 47, 61, 111 ]

usernameList = map(lambda u: u[0:-1], sys.stdin.readlines())
userrand = random.Random()

for numElements in testSizes:
   summary = dict()
   for i in range(numElements):
      summary[i] = 0
   for username in usernameList:
       userrand.seed(username)
       selected = userrand.sample(range(numElements),3)
       for slot in selected:
          summary[slot] += 1
 
   counts = summary.values()
   counts.sort()
   lowest = counts[0]
   byslot = summary.items()
   byslot.sort(cmp=lambda (k1,v1), (k2,v2): cmp(k1,k2) )
   peaks = map (lambda (s, c): (s, (c - lowest + 0.0) / len(usernameList)), byslot)
   print numElements, peaks
