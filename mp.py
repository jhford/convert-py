import Queue
import threading
import os
import logging
import time
from multiprocessing import cpu_count

# This is my attempt at a tool to run a bunch of jobs in parrallel.
# It's probably not very good and I don't really have anything in place
# for handling errors in threads yet.  Also, because of the GIL, this is
# only really useful if the threads don't do much in the python process
# and instead only call out to other programs

import util

class Job(object):
    def __init__(self):
        object.__init__(self)

    def run(self):
        raise Exception("Unimplemented")


class PyFuncJob(Job):
    def __init__(self, function, *args, **kwargs):
        Job.__init__(self)
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.function(*self.args, **self.kwargs)

    def __str__(self):
        return "%s, args: '%s', kwargs: '%s'" % \
                (str(self.function),
                 "', '".join(self.args),
                 "', '".join(['%s=%s' % (x, self.kwargs[x]) for x in
                              self.kwargs.keys()]))


class JobThread(threading.Thread):
    def __init__(self, queue, failed_queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.failed_queue = failed_queue
        self.log = logging.getLogger('convert.mp')

    def run(self):
        self.log.debug("%s reporting for duty" % self.name)
        try:
            job = self.queue.get()
            while True:
                try:
                    job.run()
                except Exception as E:
                    self.log.debug("Inserting failed job and exception into failed_queue")
                    print E
                    self.failed_queue.put((job, E))
                self.queue.task_done()
                self.log.debug("%s asking for a job" % self.name)
                job = self.queue.get(False)
        except Queue.Empty:
            self.log.debug("%s clocking out" % self.name)

class JobEnqueuer(threading.Thread):
    def __init__(self, jobs, queue):
        threading.Thread.__init__(self)
        self.jobs = jobs
        self.queue = queue
        self.log = logging.getLogger('convert.mp')

    def run(self):
        self.log.debug("Enequeueing thread %s reporting for duty" % self.name)
        for job in self.jobs:
            self.queue.put(job)
        self.log.debug("All jobs enqueued by %s" % self.name)


class ThreadPool(object):
    threads = []

    def __init__(self, jobs, thread_count=cpu_count()):
        self.jobs = jobs
        self.thread_count = thread_count

    def run_jobs(self):
        queue = Queue.Queue()
        failed_queue = Queue.Queue()
        enqueuer = JobEnqueuer(self.jobs, queue)
        enqueuer.start()
        for i in range(self.thread_count):
            thread = JobThread(queue, failed_queue)
            thread.name = 'JobThread-%d' % i
            thread.start()
            self.threads.append(thread)
        enqueuer.join()
        queue.join()
        for thread in self.threads:
            thread.join()

