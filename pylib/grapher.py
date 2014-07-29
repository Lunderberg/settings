#!/usr/bin/env python

import pylab
import numpy

def graph(func,num_points=1000,low=0.0,high=1.0,
          xtitle=None,ytitle=None,title=None):
    x = numpy.arange(low,high,(high-low)/num_points)
    y = func(x)
    pylab.plot(x,y)
    if xtitle is not None:
        pylab.xlabel(xtitle)
    if ytitle is not None:
        pylab.ylabel(ytitle)
    if title is not None:
        pylab.title(title)
