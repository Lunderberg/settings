#!/usr/bin/env python2

"""
Records commands to a directory.
Usage:
export PROMPT_COMMAND="history 1 | record_command.py"
export PROMPT_COMMAND="history 1 | record_command.py -p"

Then, each command will be written into ~/.history,
  with the filename either determined by the date,
  or by the date/PID of the shell.
"""

import datetime
import os
import sys

now = datetime.datetime.now()

if len(sys.argv)>1 and sys.argv[1]=='-p':
    import psutil
    parent = psutil.Process(os.getpid()).parent()
    par_birth = datetime.datetime.fromtimestamp(int(parent.create_time()))
    filename = 'hist_{}_pid-{}.txt'.format(par_birth.strftime('%Y-%m-%d'),parent.pid)
else:
    filename = 'hist_{}.txt'.format(now.strftime('%Y-%m-%d'))

#Make the directory and
output_dir = os.path.expanduser(os.path.join('~','.history'))
output_file = os.path.join(output_dir,filename)
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

prev_command = raw_input().split(None,1)[1]

with open(output_file,'a') as f:
    to_write = now.strftime('%Y-%m-%d_%H:%M:%S') + '\t' + prev_command + '\n'
    f.write(to_write)
