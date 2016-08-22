#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import copy
import csv
from logging import getLogger

from dysense.core.utility import wrap_angle_radians

def standardize_to_radians(angles, source, angle_type):

    # Set to false if already in radians.
    need_to_convert = True
    
    try:
        units = orientation_source_units(source)
        
        if is_radians(units):
            need_to_convert = False # already in radians
        if not is_degrees(units):
            getLogger('processing').warn('{} units \'{}\' is not recognized. Assuming degrees.'.format(angle_type.title(), units))
        
    except KeyError:
        getLogger('processing').warn('Units not listed for {} source. Assuming degrees.'.format(angle_type))

    if need_to_convert:
        # Make a copy so we don't modify the original.
        angles = copy.copy(angles)
        for angle in angles:
            angle.angle *= math.pi / 180.0

    # Temporary debug output
    if need_to_convert:
        getLogger('processing').debug('Converting {} angles to radians for geotagging.'.format(angle_type))
    else:
        getLogger('processing').debug('{} angles already in radians for geotagging.'.format(angle_type.title()))
        
    # Make sure angles are between +/- PI.
    for angle in angles:
        angle.angle = wrap_angle_radians(angle.angle)

    return angles

def is_degrees(units):
    return units.lower() in ['deg', 'degree', 'degrees']

def is_radians(units):
    return units.lower() in ['rad', 'radian', 'radians']

def orientation_source_units(orientation_source):
    
    metadata = orientation_source['metadata']
    setting_idx = orientation_source['orientation_idx']
    return metadata['data'][setting_idx]['units']

def contains_measurements(lst):
    
    return isinstance(lst, (list, tuple)) and len(lst) > 0
    
def unicode_csv_reader(utf8_file, **kwargs):
    '''Generator for reading rows of the specified file that's saved in UTF8 encoding.'''
    csv_reader = csv.reader(utf8_file, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]
