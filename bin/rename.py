#!/usr/bin/env python

"""
Goal: Input two python format strings.
      All files that match the first are then renamed according to the second.

Currently, doesn't work very well.
os.walk is overzealous, recursing even when a match is impossible.
Does not work for absolute paths, only relative paths.

Should manually recurse, checking for matches of each subpattern.
"""

import os
import sys
import parse

informat = sys.argv[1]
outformat = sys.argv[2]

maxdepth = len(os.path.split(informat))


for path,directories,filenames in os.walk(os.curdir):
    if len(os.path.split(path))>maxdepth:
        del directories[:]
    for name in directories+filenames:
        old = os.path.join(path,name)
        params = parse.parse(informat,old)
        new = outformat.format(*params.fixed)
        os.rename(old,new)
