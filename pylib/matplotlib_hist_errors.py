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


matplotlib.axes._axes.Axes.hist_errors = hist_errors


if __name__=='__main__':
    data = np.random.normal(size=10000)
    weights = 5*np.ones(shape=data.shape)

    fig, axes = plt.subplots()
    axes.hist_errors(data, weights=weights, range=(-5,5), bins=20)
    plt.show()
