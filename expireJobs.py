import argparse
import cups
import time


parser = argparse.ArgumentParser(description="remove submitted print jobs after an elapsed time")
parser.add_argument('timeout', type=int)
parser.add_argument('sleep', type=int)

args = vars(parser.parse_args())
jobTimeout = args['timeout']
sleepInterval = args['sleep']

conn = cups.Connection()

# Force the cupsd server to authenticate us by doing a
# unnecessary privillidged operation 
conn.acceptJobs('public')



jobs = dict()
while True:
   now = time.time()
   incomplete = set(conn.getJobs(which_jobs='not-completed'))
   for jobId in incomplete:
      attr = conn.getJobAttributes(jobId, ['printer-uri', 'job-id', 'time-at-creation'] )
      jobs[jobId] = (attr['time-at-creation'], attr['printer-uri'], attr['job-id'])

   for jobId in incomplete.symmetric_difference(jobs.keys()):
      del jobs[jobId]

   for (created, printerUri, jobId) in jobs.values():
       if (created + jobTimeout) < now:
          attr =  conn.getJobAttributes(jobId, ['printer-uri', 'job-id', 'time-at-creation', 'time-at-completed'])
          if attr['time-at-completed'] is None:
             conn.cancelJob(jobId, purge_job=True)

   time.sleep(30)
