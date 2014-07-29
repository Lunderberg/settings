#!/usr/bin/env python

import re
import socket

class IPRange:
    regex = re.compile("(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})")
    def __init__(self,minIP,maxIP):
        self.minIP = self.IPstrToList(minIP)
        self.maxIP = self.IPstrToList(maxIP)
        self.current = self.minIP[:]
        self.current[3] -= 1
    @classmethod
    def IPstrToList(cls,IPstr):
        m = cls.regex.match(IPstr)
        if not m:
            raise Exception("Not a valid IP address")
        return [int(m.groups()[0]),
                int(m.groups()[1]),
                int(m.groups()[2]),
                int(m.groups()[3])]
    def __iter__(self):
        return self
    def __str__(self):
        return "Start: {0}\tStop: {1}".format(
            '.'.join(str(i) for i in self.minIP),
            '.'.join(str(i) for i in self.maxIP))
    def next(self):
        if all(x==y for (x,y) in zip(self.maxIP,self.current)):
            raise StopIteration
        for i in range(3,-1,-1):
            self.current[i] += 1
            if self.current[i]==256:
                self.current[i] = 0
            else:
                break
        return '.'.join(str(i) for i in self.current)

def isOpen(ip,port,timeout=0.5):
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip,int(port)))
        s.shutdown(2)
        return True
    except (socket.timeout,socket.error):
        return False

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('-p','--port',dest='port',type=int,default=22)
    p.add_argument('-a','--addresses',dest='addresses',type=str,nargs='+',required=True)
    p.add_argument('-t','--timeout',dest='timeout',type=float,default=0.5)
    args = p.parse_args()

    for address in args.addresses:
        if isOpen(address,args.port,args.timeout):
            print address
            return

if __name__=='__main__':
    main()
