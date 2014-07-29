#!/usr/bin/env python

import os
import sys

def runOnce(*args,**kwargs):
    if running(*args,**kwargs):
        sys.exit(-1)
    else:
        return

def running(fileName):
    try:
        f = open(fileName)
    except IOError:
        running = False
    else:
        pid = int(f.readline())
        f.close()
        running = pid_is_running(pid)
    if not running:
        with open(fileName,'w') as f:
            f.write(str(os.getpid()))
    return running

def pid_is_running(pid):
    try:
        os.kill(pid,0)
    except OSError as e:
        #An error number of 3 means that the process does not exist.
        return e[0]!=3
    else:
        return True
