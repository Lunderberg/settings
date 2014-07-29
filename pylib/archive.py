#!/usr/bin/env python

import os
from shutil import rmtree
from subprocess import call

def _expand(path):
    return os.path.expandvars(os.path.expanduser(path))

def archive(src,dest,folder=None,update_currentref=True,overwrite=False):
    if folder is None:
        from datetime import datetime
        folder = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    src = _expand(src)
    if src[-1]=='/':
        src = src[:-1]
    dest = _expand(dest)

    if folder in ['currentref','temp']:
        raise ValueError("'{0}' is a protected folder name".format(folder))
    if not overwrite and os.path.exists(dest) and folder in os.listdir(dest):
        raise ValueError("{folder} already exist in {dest} without explicit overwriting".format(folder=folder,dest=dest))

    if not os.path.exists(dest):
        os.makedirs(dest)

    output = os.path.join(dest,'temp' if overwrite else folder)
    final_output = os.path.join(dest,folder)

    if "currentref" in os.listdir(dest):
        call(['rsync','-a','--link-dest','../currentref',src,output])
    else:
        call(['rsync','-a',src,output])

    if overwrite:
        if os.path.exists(final_output):
            rmtree(final_output)
        os.rename(output,final_output)

    if update_currentref:
        currentref = os.path.join(dest,"currentref")
        try:
            os.remove(currentref)
        except OSError:
            pass
        os.symlink(folder,currentref)
    

if __name__=='__main__':
    from argparse import ArgumentParser
    from sys import argv
    parser = ArgumentParser(description="Archive a folder")
    parser.add_argument('-i','--source',dest='src',
                        action='store',required=True,
                        help="The folder to be archived")
    parser.add_argument('-o','--dest',dest='dest',
                        action='store',required=True,
                        help="The folder to be sent to archive")
    parser.add_argument('-f','--subfolder',dest='folder',
                        action='store',default=None,
                        help="The subfolder to hold the archive (default to datetime)")
    parser.add_argument('-nc','--no-currentref',dest='currentref',
                        action='store_false',default=True,
                        help="Do not mark the new archive as the currentref archive.")
    args = parser.parse_args()
    archive(args.src,args.dest,args.folder,args.currentref)
