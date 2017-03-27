# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import copy
import csv

from dysense.core.utility import wrap_angle_degrees
from dysense.processing.log import log
import numpy as np
from math import sin, cos, atan2, asin

def standardize_to_degrees(angles, sensor_units, angle_type):
    '''
    Return new list of angles of the specified type (e.g. 'roll') so that the angles are in degrees and within +/- 180.
    Use sensor units to determine if the distances need to be converted or if they're already in meters.
    '''
    # Set to true if source is measured in radians.
    need_to_convert = False

    if is_radians(sensor_units):
        need_to_convert = True
    elif not is_degrees(sensor_units):
        log().warn('{} units \'{}\' is not recognized. Assuming degrees.'.format(angle_type.title(), sensor_units))

    if need_to_convert:
        # Make a copy so we don't modify the original.
        angles = copy.copy(angles)
        for angle in angles:
            angle.angle *= 180.0 / math.pi

    # Temporary debug output
    if need_to_convert:
        log().debug('Converting {} angles to degrees.'.format(angle_type))
    else:
        log().debug('{} angles already in degrees.'.format(angle_type.title()))

    # Make sure angles are between +/- 180
    for angle in angles:
        angle.angle = wrap_angle_degrees(angle.angle)

    return angles

def standardize_to_meters(distances, sensor_units, source_type):
    '''
    Return new list of distances of the specified type (e.g. 'height') so that the distances are in meters.
    Use sensor units to determine if the distances need to be converted or if they're already in meters.
    '''
    # Set to a different value if we need to convert each distance (for example 0.01 if going from cm to meters)
    scale_factor = 1

    if is_centimeters(sensor_units):
        scale_factor = 0.01
    elif is_millimeters(sensor_units):
        scale_factor = 0.001
    elif not is_meters(sensor_units):
        log().warn('{} units \'{}\' is not recognized. Assuming meters.'.format(source_type.title(), sensor_units))

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

def sensor_units(sensor_info, data_index):
    '''Return units (e.g. 'meters) for sensor output data at specified index or raise KeyError if not found.'''
    return sensor_info['metadata']['data'][data_index]['units']

def contains_measurements(lst):
    '''Return true if lst is a list that contains elements.'''
    return isinstance(lst, (list, tuple)) and len(lst) > 0

def unicode_csv_reader(utf8_file, **kwargs):
    '''Generator for reading rows of the specified file that's saved in UTF8 encoding.'''
    csv_reader = csv.reader(utf8_file, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8') for cell in row]

def effective_angle_rad(angle_deg):
    '''Return angle converted to radians or 0 if angle is Nan'''

    if math.isnan(angle_deg):
        return 0.0
    else:
        return angle_deg * math.pi / 180.0

def actual_angle_deg(sensor_angles_rad, platform_angles):
    '''Return angles where each angle is converted to degrees or NaN if the corresponding platform angle is NaN'''

    actual_sensor_angles = []
    for sensor_angle, platform_angle in zip(sensor_angles_rad, platform_angles):
        if math.isnan(platform_angle):
            actual_sensor_angles.append(float('NaN'))
        else:
            actual_sensor_angles.append(sensor_angle * 180.0 / math.pi)

    return actual_sensor_angles

def rot_child_to_parent(roll, pitch, yaw):
    '''
    Return 3x3 rotation matrix that will transform a vector in the child frame to the parent frame.
    Roll, pitch, yaw are the relative orientation of the child frame with respect to the parent frame.
    Specified angles should be in radians and represent a right-handed positive rotation.
    In terms of passive rotations (which this is because it's changing coordinate frames)
       [1] this is intrinsically (-x) then (-y) then (-z) intrinsically = about intermediate frames
       [2] this is extrinsically (-Z) then (-Y) then (-X) extrinsically = all rotations are about parent frame.
    In terms of active rotations (rotating a vector within the parent frame)
       [3] this is intrinsically (z) then (y) then (x)
       [4] this is extrinsically (X) then (Y) then (Z)

    To go the opposite direction (parent -> child) then take the transpose of this matrix which is equivalent to the inverse.
    '''
    # Pre-compute sines and cosines.
    sr = sin(roll)
    cr = cos(roll)
    sp = sin(pitch)
    cp = cos(pitch)
    sy = sin(yaw)
    cy = cos(yaw)

    return np.array([[cp*cy,  sr*sp*cy - cr*sy,  sr*sy + cr*sp*cy],
                     [cp*sy,  cr*cy + sr*sp*sy,  cr*sp*sy - sr*cy],
                     [ -sp,         sr*cp,             cr*cp     ]])


def rot_parent_to_child(roll, pitch, yaw):
    '''
    Return 3x3 rotation matrix that will transform a vector in the parent frame to the child frame.
    Roll, pitch, yaw are the relative orientation of the child frame with respect to the parent frame.
    Specified angles should be in radians and represent a right-handed positive rotation.
    In terms of passive rotations (which this is because it's changing coordinate frames)
       [1] this is intrinsically (z) then (y) then (x) intrinsically = about intermediate frames
       [2] this is extrinsically (X) then (Y) then (Z) extrinsically = all rotations are about parent frame.
    In terms of active rotations (rotating a vector within the parent frame)
       [3] this is intrinsically (-x) then (-y) then (-z)
       [4] this is extrinsically (-Z) then (-Y) then (-X)

    [1] is commonly referred to as Euler ZYX matrix.
    [2] is commonly referred to as Roll-Pitch-Yaw matrix.

    To go the opposite direction (child -> parent) then take the transpose of this matrix which is equivalent to the inverse.
    '''
    # Pre-compute sines and cosines.
    sr = sin(roll)
    cr = cos(roll)
    sp = sin(pitch)
    cp = cos(pitch)
    sy = sin(yaw)
    cy = cos(yaw)

    return np.array([[     cp*cy,             cp*sy,          -sp ],
                     [sr*sp*cy - cr*sy,  cr*cy + sr*sp*sy,   sr*cp],
                     [sr*sy + cr*sp*cy,  cr*sp*sy - sr*cy,   cr*cp]])

def rot_x(a):
    '''
    Return 3x3 positive rotation matrix about X axis by an angle 'a' specified in radians.
    This represents an active rotation, that is it will rotate a vector within a frame.
    '''
    return np.array([[1,   0,       0   ],
                     [0, cos(a), -sin(a)],
                     [0, sin(a),  cos(a)]])

def rot_y(a):
    '''
    Return 3x3 positive rotation matrix about Y axis by an angle 'a' specified in radians.
    This represents an active rotation, that is it will rotate a vector within a frame.
    '''
    return np.array([[ cos(a), 0,  sin(a)],
                     [   0,    1,    0   ],
                     [-sin(a), 0,  cos(a)]])

def rot_z(a):
    '''
    Return 3x3 positive rotation matrix about Z axis by an angle 'a' specified in radians.
    This represents an active rotation, that is it will rotate a vector within a frame.
    '''
    return np.array([[cos(a), -sin(a), 0],
                     [sin(a),  cos(a), 0],
                     [  0,       0,    1]])

def rpy_from_rot_matrix(r):
    '''
    Return [roll, pitch, yaw] angles in radians associated with active, extrinsic Roll-Pitch-Yaw matrix 'r'.
    Roll and yaw will be between +/- PI and pitch will be between +/- PI/2
    '''
    pitch = -asin(r[2,0])

    if r[2,0] == 1:
        # Negative gimbal lock (pitch at -90 deg), fix yaw and solve for roll.
        yaw = 0
        roll = atan2(-r[0,1], -r[0,2])
    elif r[2,0] == -1:
        # Positive gimbal lock (pitch at 90 deg), fix yaw and solve for roll.
        yaw = 0
        roll = atan2(+r[0,1], +r[0,2])
    else:
        # General solution.
        roll = atan2(r[2,1], r[2,2])
        yaw = atan2(r[1,0], r[0, 0])

    return [roll, pitch, yaw]

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
