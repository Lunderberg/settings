#!/usr/bin/env python

import matplotlib as mpl
import matplotlib.pyplot as plt

# TODO: http://stackoverflow.com/a/15312706/2689797, to adjust the tick labels

def load_style():
    # # Alternatively, place this in the .matplotlibrc
    # lines.linewidth: 2
    # patch.linewidth: 2
    # axes.color_cycle: black, blue, green, red, cyan, magenta, yellow
    # axes.linewidth: 2
    # axes.labelsize: 18
    # xtick.major.size: 10
    # xtick.major.width: 2
    # ytick.major.size: 10
    # ytick.major.width: 2
    # xtick.labelsize: large
    # ytick.labelsize: large
    # figure.facecolor: white
    # legend.loc: best
    mpl.rc('lines', linewidth=2)
    mpl.rc('patch', linewidth=2)
    mpl.rc('axes',
                  color_cycle=['black','blue','green','red','cyan','magenta','yellow'],
                  linewidth=2,
                  labelsize=18)
    mpl.rc('xtick.major',width=2, size=10)
    mpl.rc('ytick.major',width=2, size=10)
    mpl.rc('xtick',labelsize='large')
    mpl.rc('ytick',labelsize='large')
    mpl.rc('figure', facecolor='white')
    mpl.rc('legend', loc='best')

def sample_hist():
    from random import gauss

    fig = plt.figure()
    axes = fig.add_subplot(1,1,1)

    data = [gauss(0,1) for _ in range(1000)]
    hist = axes.hist(data, histtype='step')
    axes.set_xlabel('Energy (keV)')
    axes.set_ylabel('Counts')

def sample_plot():
    import numpy as np

    fig = plt.figure()
    axes = fig.add_subplot(1,1,1)

    xvals = np.arange(0,720,1)
    yvals = np.cos(xvals * (np.pi/180))

    axes.plot(xvals, yvals)

if __name__=='__main__':
    load_style()
    sample_plot()
    sample_hist()
    plt.show()
