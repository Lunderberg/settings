#!/usr/bin/env python3

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import sys

def get_varnames(func):
    if sys.version_info[0] < 3:
        return func.func_code.co_varnames
    else:
        return func.__code__.co_varnames

def hist_errors(self, *args, **kwargs):
    kwargs.update(dict(zip(get_varnames(self.hist)[1:], args)))

    kwargs['histtype'] = 'step'
    bin_content, bin_edges, hist_patch = self.hist(**kwargs)

    hist_kwargs = {key:value for key,value in kwargs.items()
                   if key in get_varnames(np.histogram)}

    if 'weights' in hist_kwargs:
        hist_kwargs['weights'] = hist_kwargs['weights']**2

    sumw2, _ = np.histogram(kwargs['x'], **hist_kwargs)
    bin_errors = np.sqrt(sumw2)

    edges = np.array([a
                      for b in zip(bin_edges[:-1],bin_edges[1:])
                      for a in b])
    contents = np.array([a
                         for b in zip(bin_content, bin_content)
                         for a in b])
    errors = np.array([a
                       for b in zip(bin_errors,bin_errors)
                       for a in b])

    fill_patch = self.fill_between(edges, contents-errors, contents+errors,
                                   color='gray')

    return (bin_content, bin_edges, bin_errors,
            [hist_patch, fill_patch])

def better_step(self, x, y, *args, **kwargs):
    if len(x) == len(y)+1:
        y = np.insert(y, 0, y[0])
    self.step(x, y, *args, **kwargs)

def fill_between_step(self, x, y1, y2, *args, **kwargs):
    if len(x) == len(y1):
        x = np.array(x)
        first_point = x[0] - (x[1] - x[0])/2.0
        middle = x[:-1] + (x[1:] - x[:-1])/2.0
        last_point = x[-1] + (x[-1] - x[-2])/2.0
        x = np.concatenate(([first_point], middle, [last_point]))

    x = [a for b in zip(x[:-1],x[1:]) for a in b]
    y1 = [a for b in zip(y1, y1) for a in b]
    y2 = [a for b in zip(y2, y2) for a in b]

    self.fill_between(x, y1, y2, *args, **kwargs)



matplotlib.axes._axes.Axes.hist_errors = hist_errors
matplotlib.axes._axes.Axes.better_step = better_step
matplotlib.axes._axes.Axes.fill_between_step = fill_between_step


if __name__=='__main__':
    data = np.random.normal(size=10000)
    weights = 5*np.ones(shape=data.shape)

    fig, axes = plt.subplots()
    axes.hist_errors(data, weights=weights, range=(-5,5), bins=20)
    plt.show()
