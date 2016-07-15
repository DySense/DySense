#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from dysense.core.utility import make_unicode, make_utf8

u = '字字'
u = make_utf8(u)
#print u

l = u'{}'.format(u)
print l
l = b'{}'.format(u)
print l

u = 'idzie wąż wąską dróżką'.encode('utf8')
print type(u)
u = str(u)
print u

uu = u.decode('utf8')
print(uu)
s = uu.encode('cp1250')
print(s)