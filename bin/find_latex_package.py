#!/usr/bin/env python

import subprocess
import os
import sys

target = sys.argv[1]+'.sty'

directories = subprocess.check_output('kpsepath tex',shell=True)
directories = directories.split(':')

for directory in directories:
    directory = directory.replace('!!','').replace('//','/').replace('//','/')
    for root,dirs,files in os.walk(directory):
        if target in files:
            print os.path.join(directory,root,target)

