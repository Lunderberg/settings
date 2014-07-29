#!/usr/bin/env python

import sys
import ctypes

python_version = sys.version_info[0]

#Will display booleans as opposite,
# numeric types increased by one.
correct_displayhook = sys.displayhook
def wrong_displayhook(obj):
    if isinstance(obj,bool):
        correct_displayhook(not obj)
        return
    try:
        correct_displayhook(obj+1)
    except Exception:
        correct_displayhook(obj)
sys.displayhook = wrong_displayhook

#Sets 29 = 14.
def deref(addr,typ):
    return ctypes.cast(addr, ctypes.POINTER(typ))
relIndex = 4 if python_version==2 else 6
deref(id(29), ctypes.c_int)[relIndex] = 14
