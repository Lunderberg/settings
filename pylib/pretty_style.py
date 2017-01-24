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
           # K. Kelly's color cycle
           #color_cycle = ['#F2F3F4', '#222222', '#F3C300', '#875692', '#F38400', '#A1CAF1', '#BE0032', '#C2B280', '#848482', '#008856', '#E68FAC', '#0067A5', '#F99379', '#604E97', '#F6A600', '#B3446C', '#DCD300', '#882D17', '#8DB600', '#654522', '#E25822', '#2B3D26'],
           # color_cycle = [#"#000000",
           #                "#FFFF00", "#1CE6FF", "#FF34FF", "#FF4A46", "#008941", "#006FA6", "#A30059",
           #                "#FFDBE5", "#7A4900", "#0000A6", "#63FFAC", "#B79762", "#004D43", "#8FB0FF", "#997D87",
           #                "#5A0007", "#809693", "#FEFFE6", "#1B4400", "#4FC601", "#3B5DFF", "#4A3B53", "#FF2F80",
           #                "#61615A", "#BA0900", "#6B7900", "#00C2A0", "#FFAA92", "#FF90C9", "#B903AA", "#D16100",
           #                "#DDEFFF", "#000035", "#7B4F4B", "#A1C299", "#300018", "#0AA6D8", "#013349", "#00846F",
           #                "#372101", "#FFB500", "#C2FFED", "#A079BF", "#CC0744", "#C0B9B2", "#C2FF99", "#001E09",
           #                "#00489C", "#6F0062", "#0CBD66", "#EEC3FF", "#456D75", "#B77B68", "#7A87A1", "#788D66",
           #                "#885578", "#FAD09F", "#FF8A9A", "#D157A0", "#BEC459", "#456648", "#0086ED", "#886F4C",
           #                "#34362D", "#B4A8BD", "#00A6AA", "#452C2C", "#636375", "#A3C8C9", "#FF913F", "#938A81",
           #                "#575329", "#00FECF", "#B05B6F", "#8CD0FF", "#3B9700", "#04F757", "#C8A1A1", "#1E6E00",
           #                "#7900D7", "#A77500", "#6367A9", "#A05837", "#6B002C", "#772600", "#D790FF", "#9B9700",
           #                "#549E79", "#FFF69F", "#201625", "#72418F", "#BC23FF", "#99ADC0", "#3A2465", "#922329",
           #                "#5B4534", "#FDE8DC", "#404E55", "#0089A3", "#CB7E98", "#A4E804", "#324E72", "#6A3A4C",],
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

# Because I'm lazy, and want this to happen by default
load_style()

if __name__=='__main__':
    sample_plot()
    sample_hist()
    plt.show()
