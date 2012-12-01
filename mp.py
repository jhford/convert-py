import Queue
import threading
import os
import logging
import time

# This is my attempt at a tool to run a bunch of jobs in parrallel.
# It's probably not very good and I don't really have anything in place
# for handling errors in threads yet.  Also, because of the GIL, this is
# only really useful if the threads don't do much in the python process
# and instead only call out to other programs

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

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        print "%s reporting for duty" % self.name
        try:
            job = self.queue.get()
            while True:
                print "Running: ", str(job)
                job.run()
                self.queue.task_done()
                print "%s asking for a job" % self.name
                job = self.queue.get(False)
        except Queue.Empty:
            print "%s clocking out" % self.name

class JobEnqueuer(threading.Thread):
    name='Enqueuer'
    def __init__(self, jobs, queue):
        threading.Thread.__init__(self)
        self.jobs = jobs
        self.queue = queue

    def run(self):
        print "Enequeueing thread %s reporting for duty" % self.name
        for job in self.jobs:
            self.queue.put(job)
        print "All jobs enqueued by %s" % self.name

class ThreadMonitor(threading.Thread):
    def __init__(self, threads, thread_count=4

class ThreadPool(object):
    threads = []

    def __init__(self, jobs, thread_count=4, max_job_in_thread=2):
        self.jobs = jobs
        self.thread_count = thread_count
        self.max_job_in_thread = max_job_in_thread

    def start_thread(self, queue):
        thread = JobThread(queue)
        thread.daemon = True
        thread.start()
        return thread

    def run_jobs(self):
        queue = Queue.Queue()
        enqueuer = JobEnqueuer(self.jobs, queue)
        enqueuer.start()
        for i in range(self.thread_count):
            self.threads.append(self.start_thread(queue))
        enqueuer.join()
        queue.join()
        for thread in self.threads:
            thread.join()

