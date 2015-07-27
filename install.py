#!/usr/bin/env python

import os
import sys
import subprocess
import tarfile
import shutil
from glob import glob
import pkgutil
import platform

fold = os.path.abspath(os.path.dirname(sys.argv[0]))
system = platform.system()

def path(*args):
    return os.path.expanduser(os.path.expandvars(
            os.path.join(*args)))

#Because windows is absurd and has no easy way to make symlinks.
#This also requires the script to be run as admin, since symlinks are restricted to admins
#How was that ever a good idea?
def symlink(source, link_name):
    os_symlink = getattr(os, "symlink", None)
    if callable(os_symlink):
        os_symlink(source, link_name)
    else:
        import ctypes
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        flags = 1 if os.path.isdir(source) else 0
        if csl(link_name, source, flags) == 0:
            raise ctypes.WinError()

def link(source,dest):
    source = os.path.join(fold,source)
    dest = path(dest)
    if os.path.exists(dest):
        print "{0} exists, not overwriting".format(dest)
    else:
        if os.path.lexists(dest):
            os.remove(dest)
        symlink(source,dest)
        print "{0} linked to {1}".format(dest,source)

git_bin = 'git' if system=='Linux' else 'c:/Program Files (x86)/Git/bin/git.exe'
def clone_git(url,outputDir):
    name = url[url.rfind('/')+1:url.rfind('.')]
    outputDir = os.path.join(path(outputDir),name)
    if os.path.exists(outputDir):
        print '{} exists, skipping'.format(outputDir)
        return
    subprocess.call([git_bin,'clone','--recursive',url,outputDir])
    print 'Installed {}'.format(outputDir)

installed_pypackages = [name for _,name,_ in pkgutil.iter_modules()]
def installPyPackage(tarball):
    tarpath,filename = os.path.split(tarball)
    for name in installed_pypackages:
        if name in filename:
            print '{} installed already, skipping'.format(name)
            return
    tar = tarfile.open(tarball,'r:gz')
    instpath = path(tarpath,tar.firstmember.name)
    tar.extractall(tarpath)
    subprocess.call(['python','setup.py','install','--user'],
                    cwd=instpath,stdout=open(os.devnull,'wb'))
    shutil.rmtree(instpath)
    print 'Installed {0}'.format(instpath)

dot_emacs_path = '~' if system=='Linux' else path('~','AppData','Roaming')
emacs_dir = path(dot_emacs_path,'.emacs.d')
dot_emacs = path(dot_emacs_path,'.emacs')

if system=='Linux':
    link('dot_bash_common','~/.bash_common')
    link('dot_screenrc','~/.screenrc')
    link('dot_dir_colors','~/.dir_colors')
    link('dot_tmux.conf','~/.tmux.conf')
    link('dot_gitconfig','~/.gitconfig')
    link('dot_Xdefaults','~/.Xdefaults')

link('pylib','~/pylib')
link('dot_emacs',dot_emacs)
link('dot_emacs.d',emacs_dir)

for tarball in sorted(glob(path('pypackages','*.tar.gz'))+
                      glob(path('pypackages','*.tgz'))):
    installPyPackage(tarball)
