#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time

# measure the smallest time delta by spinning until the time changes
def measure():
    t0 = time.time()
    t1 = t0
    while t1 == t0:
        t1 = time.time()
    return (t0, t1, t1-t0)

# 1000 sample average
print reduce(lambda a,b:a+b, [measure()[2] for i in range(1000)], 0.0) / 1000.0

# print off 10 results
samples = [measure() for i in range(10)]
for s in samples:
    print s