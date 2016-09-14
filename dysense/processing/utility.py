# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import copy
import csv
from logging import getLogger

from dysense.core.utility import wrap_angle_degrees

def standardize_to_degrees(angles, source, angle_type):
    '''
    Return new list of angles of the specified type (e.g. 'roll') so that the angles are in degrees and within +/- 180.
    Use the source metadata to determine if the angles need to be converted or if they're already in degrees.
    ''' 
    # Set to true if source is measured in radians.
    need_to_convert = False
    
    try:
        units = source_units(source, 'orientation_index')
        
        if is_radians(units):
            need_to_convert = True 
        elif not is_degrees(units):
            getLogger('processing').warn('{} units \'{}\' is not recognized. Assuming degrees.'.format(angle_type.title(), units))
        
    except KeyError:
        getLogger('processing').warn('Units not listed for {} source. Assuming degrees.'.format(angle_type))

    if need_to_convert:
        # Make a copy so we don't modify the original.
        angles = copy.copy(angles)
        for angle in angles:
            angle.angle *= 180.0 / math.pi

    # Temporary debug output
    if need_to_convert:
        getLogger('processing').debug('Converting {} angles to degrees.'.format(angle_type))
    else:
        getLogger('processing').debug('{} angles already in degrees.'.format(angle_type.title()))
        
    # Make sure angles are between +/- 180
    for angle in angles:
        angle.angle = wrap_angle_degrees(angle.angle)

    return angles

def standardize_to_meters(distances, source, source_type):
    '''
    Return new list of distances of the specified type (e.g. 'height') so that the distances are in meters.
    Use the source metadata to determine if the distances need to be converted or if they're already in meters.
    ''' 
    # Set to a different value if we need to convert each distance (for example 0.01 if going from cm to meters)
    scale_factor = 1
    
    try:
        units = source_units(source, 'height_index')

        if is_centimeters(units):
            scale_factor = 0.01
        elif is_millimeters(units):
            scale_factor = 0.001
        elif not is_meters(units):
            getLogger('processing').warn('{} units \'{}\' is not recognized. Assuming meters.'.format(source_type.title(), units))
        
    except KeyError:
        getLogger('processing').warn('Units not listed for {} source. Assuming meters.'.format(source_type))

    need_to_convert = scale_factor != 1

    if need_to_convert:
        # Make a copy so we don't modify the original.
        distances = copy.copy(distances)
        for distance in distances:
            distance.value *= scale_factor

    return distances

def is_degrees(units):
    return units.lower() in ['deg', 'degree', 'degrees']

def is_radians(units):
    return units.lower() in ['rad', 'radian', 'radians']

def is_meters(units):
    return units.lower() in ['m', 'meter', 'meters']

def is_centimeters(units):
    return units.lower() in ['cm', 'centimeter', 'centimeters']

def is_millimeters(units):
    return units.lower() in ['mm', 'millimeter', 'millimeters']

def source_units(source, index_name):
    '''Return units (e.g. 'meters) for source output data at specified index name or raise KeyError if not found.'''
    metadata = source['metadata']
    setting_idx = source[index_name]
    return metadata['data'][setting_idx]['units']

def contains_measurements(lst):
    '''Return true if lst is a list that contains elements.'''
    return isinstance(lst, (list, tuple)) and len(lst) > 0
    
def unicode_csv_reader(utf8_file, **kwargs):
    '''Generator for reading rows of the specified file that's saved in UTF8 encoding.'''
    csv_reader = csv.reader(utf8_file, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]
        
def filter_down_platform_state(session, max_rate):
    '''
    Updates 'platform_state' key in session to not store any entries faster than specified rate.
    If rate is less than or equal to zero then won't limit entries at all.
    '''
    states = session['platform_states']
    
    if max_rate <= 0.0 or len(states) == 0:
        return # Don't limit platform state at all.
    
    min_time_between_states = 1.0 / max_rate
    
    # Add in a little wiggle room since time won't be exact. 
    min_time_between_states *= 0.9
    
    filtered_states = []
    last_state_time = states[0].utc_time
    for state in states[1:]:
        if state.utc_time - last_state_time >= min_time_between_states:
            filtered_states.append(state)
            last_state_time = state.utc_time

    session['platform_states'] = filtered_states

class ObjectState(object):
    '''Represent the state of an object, such as a sensor or a platform.'''
    
    def __init__(self, utc_time, lat, long, alt, roll, pitch, yaw, height_above_ground):
        '''Constructor'''
        self.utc_time = utc_time
        self.lat = lat
        self.long = long
        self.alt = alt
        
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        
        self.height_above_ground = height_above_ground

    @property
    def position(self):
        return (self.lat, self.long, self.alt)
    
    @property
    def orientation(self):
        return (self.roll, self.pitch, self.yaw)

class StampedPosition(object):
    '''Time stamped position measurement.'''
    
    def __init__(self, utc_time, lat, long, alt):
        self.utc_time = utc_time
        self.lat = lat
        self.long = long
        self.alt = alt
        
    @property
    def position_tuple(self):
        return (self.lat, self.long, self.alt)
        
class StampedAngle(object):
    '''Time stamped angle measurement.'''
    
    def __init__(self, utc_time, angle):
        self.utc_time = utc_time
        self.angle = angle
        
class StampedHeight(object):
    '''Time stamped height above ground measurement.'''
    
    def __init__(self, utc_time, height):
        self.utc_time = utc_time
        self.height = height
