#!/usr/bin/env python

from scipy import integrate
import numpy

def ode_solve(first_derivative,start_time,initial_conditions,
              steps=None,final_time=None,delta_t=None):
    if (steps is None) + (final_time is None) + (delta_t is None)>1:
        raise TypeError('Required arg: Need 2 of 3 of steps, final_time, and delta_t.')
    if delta_t is not None:
        if steps is None:
            steps = int( (final_time-start_time)/delta_t)
        elif final_time is None:
            final_time = steps*delta_t + start_time

    solver = integrate.ode(first_derivative).set_integrator('dopri5')
    solver.set_initial_value(initial_conditions,start_time)
    xvals = numpy.linspace(start_time,final_time,steps)
    yvals = [initial_conditions]
    for x in xvals[1:]:
        solver.integrate(x)
        yvals.append(solver.y)
    return xvals,numpy.array(yvals)
