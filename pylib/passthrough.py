#!/usr/bin/env python

import subprocess
from threading import Thread
import sys
from datetime import datetime
from time import sleep
import re
from collections import namedtuple

class FuncCall(Thread):
    def __init__(self,func,*args,**kwargs):
        super(FuncCall,self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = True
    def run(self):
        self.result = self.func(*self.args,**self.kwargs)

class Condition:
    def __init__(self,regex,func,priority=0,count=None):
        self.string = None
        if isinstance(regex,str):
            self.string = regex
            regex = re.compile(regex)
        self.regex = regex
        self.func = func
        self.priority = priority
        self.count = count
        self.done = False
    def __call__(self,line):
        if self.regex.search(line):
            if self.count is not None:
                self.count -= 1
                if self.count==0:
                    self.done = True
            t = FuncCall(self.func,line)
            t.start()
            return True
        else:
            return False
    def __str__(self):
        if self.string is None:
            output = '{string}\t{func}\t{count}'
        else:
            output = '{func}\t{count}'
        return output.format(string=self.string,
                             func=self.func,
                             count=self.count)

class ReadOutput(Thread):
    def __init__(self,filein,findAll=True,*args,**kwargs):
        super(ReadOutput,self).__init__(*args,**kwargs)
        self.filein = filein
        self.conditions = []
        self.findAll=findAll
    def ProcessLine(self,line):
        #Perform each function until one of the functions returns False.
        #These are done in decreasing order of priority.
        for cond in self.conditions:
            result = cond(line)
            if result and not self.findAll:
                break
        self.conditions = [cond for cond in self.conditions if not cond.done]
    def AddCond(self,cond):
        self.conditions.append(cond)
        self.conditions.sort(key=lambda i:i.priority,reverse=True)
    def run(self):
        while not self.filein.closed:
            line = self.filein.readline()
            if line:
                self.ProcessLine(line)

class PassThrough:
    def __init__(self,proc_args,cwd=None):
        self.proc_args = proc_args
        self.cwd = cwd
        self.ProgConds = []
        self.UserConds = []
        self.running = False
    def AddUserCond(self,*args,**kwargs):
        if self.running:
            self.UserInThread.AddCond(Condition(*args,**kwargs))
        else:
            self.UserConds.append(Condition(*args,**kwargs))
    def AddProgCond(self,*args,**kwargs):
        if self.running:
            self.ProcOutThread.AddCond(Condition(*args,**kwargs))
        else:
            self.ProgConds.append(Condition(*args,**kwargs))
    def UserInput(self,line):
        if self.running:
            self.UserInThread.ProcessLine(line)
        else:
            raise Exception("Program not currently running")
    def run(self):
        proc = subprocess.Popen(
            self.proc_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            cwd=self.cwd)

        self.UserInThread = ReadOutput(sys.stdin,findAll=False)
        self.UserInThread.daemon = True
        for cond in self.UserConds:
            self.UserInThread.AddCond(cond)
        self.UserInThread.AddCond(Condition('',proc.stdin.write,priority=-100))
        self.UserInThread.start()

        self.ProcOutThread = ReadOutput(proc.stdout,findAll=True)
        self.ProcOutThread.daemon = True
        for cond in self.ProgConds:
            self.ProcOutThread.AddCond(cond)
        self.ProcOutThread.AddCond(Condition('',sys.stdout.write,priority=-100))
        self.ProcOutThread.start()

        self.running = True
        proc.wait()
        self.running = False

if __name__=='__main__':
    p = PassThrough(sys.argv[1:])
    p.run()
