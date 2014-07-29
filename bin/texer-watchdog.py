#!/usr/bin/env python

import sys
import time
import os
import os.path
import subprocess
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

def expand(file):
    return os.path.expanduser(os.path.expandvars(file))

class Texer(PatternMatchingEventHandler):
    def CompileLatex(self,src):
        dir,file = os.path.split(src)
        print '{0}: Compiling {1}'.format(datetime.now(),src)
        subprocess.call('scons -u',
                        stdout=open(os.devnull,'wb'), cwd=dir, shell=True)
        print '{0}: Finished'.format(datetime.now())
    def on_any_event(self,event):
        src = event.src_path
        if os.path.exists(src):
            self.CompileLatex(src)

def main(folders):
    observer = Observer()
    for fold in folders:
        event_handler = Texer(patterns=['*.tex'],
                              ignore_directories=True)
        observer.schedule(event_handler,fold,recursive=True)
    observer.start()
    print '{0}: Started'.format(datetime.now())
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__=='__main__':
    main([expand(f) for f in sys.argv[1:]]
         if len(sys.argv)>1 else ['.'])
