#!/usr/bin/env python

"""
seasideSubmit will run a series of commands in parallel.
Pass a list of commands to be run in parallel,
  and the number of worker threads to use.
"""

import random
import os

#Requests:
# nodes: The number of CPUs to be reserved, per job.
# walltime: The runtime of the job.
# mem: The memory to request.
# vmem: The virtual memory to request.

contents = """
#!/bin/bash

### name of the job
#PBS -N {name}
### email on _a_bort, _b_egin, _e_nd
#PBS -m {email}
### combine stdout/stderr
#PBS -j {join}
### time request (in HH:MM:SS)
#PBS -l {reqs}

cd ${{PBS_O_WORKDIR}}
{command}
""".strip()

def expand(path):
    return os.path.expanduser(os.path.expandvars(path))

def seasideSubmit(commands,walltime='10:00:00',nodes=1,name=None,email='abe',join='oe',**reqs):
    #Some default values, and input handling.
    if name is None:
        name = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(5))
    if isinstance(commands,str):
        commands = [commands]
    reqs['nodes'] = nodes
    reqs['walltime'] = walltime
    reqs = ','.join('{0}={1}'.format(key,val) for key,val in reqs.items())
    #Pick a script directory, then make sure it is valid.
    scriptDir = (expand(os.environ['SEASIDE_SCRIPT_DIR'])
                 if 'SEASIDE_SCRIPT_DIR' in os.environ
                 else expand('~/.seaside_scripts'))
    if not os.path.exists(scriptDir):
        os.makedirs(scriptDir)
    elif not os.path.isdir(scriptDir):
        raise EnvironmentError('{0} exists and is not a directory')
    
    #Make each script, then submit them.
    for i,command in enumerate(commands):
        fileName = name + '.' + str(i) + '.sh'
        fileContents = contents.format(name=fileName,email=email,join=join,reqs=reqs,command=command)
        fileName = os.path.join(scriptDir,fileName)
        with open(fileName,'w') as f:
            f.write(fileContents)
        command = 'ssh seaside "cd {pwd}; qsub {fileName}" > /dev/null 2> /dev/null'.format(pwd=os.getcwd(),fileName=fileName)
        os.system(command)
        
