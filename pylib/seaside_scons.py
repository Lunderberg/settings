#!/usr/bin/env python

import subprocess
import os
import random
import time
from string import ascii_letters
import xml.etree.ElementTree as XML_Tree
from datetime import datetime, timedelta


"""
Runs each command from scons as a separate job on the seaside cluster.
Useful for calibrating large datasets.

Usage:
import seaside_scons
env = Environment()
env['SPAWN'] = seaside_scons.spawn
"""

#Requests:
# nodes: The number of CPUs to be reserved, per job.
# walltime: The runtime of the job.
# mem: The memory to request.
# vmem: The virtual memory to request.

seaside_reqs = {}
keep_script = False
keep_stdout = False
#Random time waited to avoid too many submissions.
submission_spread = 30

contents = """
#!/bin/bash

### name of the job
#PBS -N {name}
### email on _a_bort, _b_egin, _e_nd
###PBS -m {email}
### combine stdout/stderr
#PBS -j {join}
### time request (in HH:MM:SS)
#PBS -l {reqs}

{env}

cd ${{PBS_O_WORKDIR}}
set -o pipefail
{command}
exit $?
""".strip()



username = os.getenv('USER')+'@seaside.nscl.msu.edu'
class QStat(object):
    def __init__(self):
        self._jobs = []
        self.last_updated = datetime.min
    def update(self):
        command = ['ssh','seaside','qstat -x']
        proc = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr = proc.communicate()
        xml = XML_Tree.fromstring(stdout)
        self._jobs[:] = [job for job in xml.getchildren() if job.find('Job_Owner').text==username]
    @property
    def jobs(self):
        if datetime.now()-self.last_updated < timedelta(seconds=60):
            return self._jobs
        else:
            for _ in range(10):
                try:
                    self.update()
                except ParseError as e:
                    time.sleep(1)
                else:
                    break
            else:
                raise e
            self.last_updated = datetime.now()
            return self._jobs
    def job_info(self,job_desc):
        for job in self.jobs:
            if (job.find('Job_Name').text==job_desc or
                job.find('Job_Id').text==job_desc):
                return {ch.tag:ch.text for ch in job.getchildren()}
        return None
qstat = QStat()

def spawn( sh, escape, cmd, args, env ):
    time.sleep(random.uniform(0,submission_spread))

    command = ' '.join(args)
    asciienv = '\n'.join('export {var}={val}'.format(var=key,val=escape(value))
                         for key,value in env.iteritems()
                         if key!='module' and '()' not in key) #don't manually set module, because it misbehaves
    #Pick a script directory, then make sure it is valid.
    scriptDir = (os.path.expanduser(os.path.expandvars(os.environ['SEASIDE_SCRIPT_DIR']))
                 if 'SEASIDE_SCRIPT_DIR' in os.environ
                 else os.path.expanduser('~/.seaside_scripts'))
    if not os.path.exists(scriptDir):
        os.makedirs(scriptDir)
    elif not os.path.isdir(scriptDir):
        raise EnvironmentError('{0} exists and is not a directory')

    reqs = {
        'nodes':1,
        'walltime':'10:00:00',
        }
    form = {
        'name':''.join(random.choice(ascii_letters) for i in range(5))+'.'+cmd,
        'email':'abe',
        'join':'oe',
        'command':command,
        'env':asciienv,
        }
    reqs.update(seaside_reqs)
    form['reqs'] = ','.join('{}={}'.format(key,val) for key,val in reqs.iteritems())

    script_name = os.path.join(scriptDir,form['name']+'.sh')
    with open(script_name,'w') as f:
        f.write(contents.format(**form))

    # Run qsub, retrieving job ID from stdout
    command = 'ssh seaside "cd {pwd}; qsub {filename}"'.format(pwd=os.getcwd(),filename=script_name)
    proc = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
    stdout,stderr = proc.communicate()

    time.sleep(10)
    qstat.update()
    while True:
        job_info = qstat.job_info(form['name'])
        if job_info['job_state']=='C':
            break
        time.sleep(30)

    returncode = int(job_info['exit_status'])

    # Delete intermediate files, unless asked for them, or if the job finished with an error.
    if not keep_script and not returncode:
        os.remove(script_name)
    if not keep_stdout and not returncode:
        stdout_filename = job_info['Output_Path']
        stdout_filename = stdout_filename[len(job_info['server'])+1:]
        os.remove(stdout_filename)

    return returncode
