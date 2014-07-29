#!/usr/bin/env python

"""
bashRun will run a series of commands in parallel.
The function bashRun.bashRun(commands,numWorkers=2) should be used.
Pass a list of commands to be run in parallel,
  and the number of worker threads to use.
"""

import threading
from Queue import Queue
import os
from time import sleep

class _Worker(threading.Thread):
    def __init__(self,queue,doneEvent,dryrun=False,verbose=True):
        super(_Worker,self).__init__()
        self.daemon = True
        self.queue = queue
        self.doneEvent = doneEvent
        self.dryrun = dryrun
        self.verbose = verbose
    def run(self):
        while True:
            command = self.queue.get()
            if not self.doneEvent.is_set():
                if self.verbose:
                    print command
                if not self.dryrun:
                    res = os.system(command)
                    #If the command was interrupted by Ctrl-C
                    if res==2:
                        self.doneEvent.set()
            self.queue.task_done()

def bashRun(commands,numWorkers=2,dryrun=False,verbose=False):
    queue = Queue()
    doneEvent = threading.Event()
    for i in range(numWorkers):
        t = _Worker(queue,doneEvent,dryrun,verbose)
        t.start()
    for command in commands:
        queue.put(command)
    queue.join()
