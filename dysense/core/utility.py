# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import subprocess
import json
import csv
import bisect
import math
import datetime
import logging
from decimal import Decimal

def find_last_index(list_to_search, element):
    try:
        return (len(list_to_search) - 1) - list_to_search[::-1].index(element)
    except ValueError:
        return -1 # element not found at all
    
def element_index(value, lst):
    '''Return index of 'value' in lst or raise IndexError if not found or ValueError if multiple matches.'''
    matching_indices = [idx for idx, elem in enumerate(lst) if elem == value]
    if len(matching_indices) > 1:
        raise ValueError('Multiple values of "{}" found in list.'.format(value))
    try:
        return matching_indices[0]
    except IndexError:
        raise IndexError('Value {} not found in list.'.format(value))
    
def get_from_list(lst, idx):
    try:
        return lst[idx]
    except IndexError:
        return None
    
def pretty(text):
    return text.replace('_',' ').replace('-',' ').title()

def format_id(id_str):
    return id_str.strip().replace(' ', '-').replace('_','-')

def make_unicode(val, errors='replace'):
    '''Return 'val' but as a unicode object. 'val' must be able to be converted to a bytestring (i.e. str).''' 
    if type(val) != unicode:
        # First convert to bytes (str) in case it was an numeric type and
        # then decode it as utf8, which will also work for ascii text.
        # If 'val' is already utf8 then the str() will have no effect and will just decode.
        return unicode(str(val), 'utf8', errors=errors)
    else:
        return val # already unicode so don't re-decode it.
    
def make_utf8(val):
    '''Return 'val' but as a UTF-8 encoded bytestring.''' 
    return make_unicode(val).encode('utf8')

def format_decimal_places(float_value, desired_num_decimals):

    return '{:.{prec}f}'.format(float_value, prec=desired_num_decimals)

def limit_decimal_places(float_value, desired_num_decimals):
    
    actual_num_decimals = abs(Decimal(float_value).as_tuple().exponent)
                    
    if actual_num_decimals > desired_num_decimals: 
        return format_decimal_places(float_value, desired_num_decimals)
     
    # Don't need to limit number of decimal places.               
    return make_unicode(float_value)

def validate_setting(value, setting_metadata):
    
    expected_type = setting_metadata.get('type', 'type_not_listed')
    
    try:
        value = validate_type(value, expected_type)
    except ValueError:
        raise ValueError("{} cannot be converted into the expected type '{}'".format(value, expected_type))

    min_value = setting_metadata.get('min_value', None)
    if min_value is not None and value < min_value:
        raise ValueError("Value can't be less than {}".format(min_value)) 
    
    max_value = setting_metadata.get('max_value', None)
    if max_value is not None and value > max_value:
        raise ValueError("Value can't be greater than {}".format(max_value)) 

    return value

def validate_type(value, expected_type):
    '''
    Return value cast to expected type, or if cast is invalid than raise ValueError.
    If value is None then will return None.
    '''
    if value is None:
        return None
    
    expected_type = expected_type.lower()

    if expected_type in ['int', 'integer']:
        value = int(value)
    elif expected_type in ['str', 'string']:
        value = make_unicode(value)
    elif expected_type in ['float', 'double']:
        value = float(value)
    elif expected_type in ['bool', 'boolean']:
        if make_unicode(value).lower() in ['true', 'yes', 't', 'y']:
            value = True
        elif make_unicode(value).lower() in ['false', 'no', 'f', 'n']:
            value = False
        else:
            raise ValueError
    else:
        raise ValueError("Invalid type {}".format(expected_type))

    return value

def open_directory_in_viewer(out_directory):
    
    if not os.path.exists(out_directory):
        return 
    
    if sys.platform == 'win32':
        os.startfile(out_directory)
    elif sys.platform == 'darwin': # MacOS
        subprocess.Popen(['open', out_directory])
    else:
        try:
            subprocess.Popen(['xdg-open', out_directory])
        except OSError:
            pass # can't open
        
def json_dumps_unicode(msg):
    return json.dumps(msg, ensure_ascii=False).encode('utf8')

def json_loads_unicode(stream):
    return json.loads(stream, ensure_ascii=False, encoding='utf8')

def yaml_load_unicode(stream):
    import yaml
    from yaml import Loader, SafeLoader
    
    def construct_yaml_str(self, node):
        # Override the default string handling function 
        # to always return unicode objects
        return self.construct_scalar(node)
    
    Loader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)
    SafeLoader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)
    
    return yaml.load(stream)

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    
    def utf_8_encoder_generator(uni_csv_data):
        for line in uni_csv_data:
            yield line.encode('utf-8')
    
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder_generator(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]
        
def utf_8_encoder(original_data):
    
    return [make_unicode(data).encode('utf8') for data in original_data]

def decode_command_line_arg(arg):
    '''Convert argument from command line (passed in as str) to unicode.'''
    return arg.decode(sys.getfilesystemencoding())

def is_list_or_tuple(lst):
    
    return isinstance(lst, (list, tuple))

def find_less_than_or_equal(a, x):
    '''
    Return rightmost index in list a where the value at a[i] is less than or equal to x.
    If x is greater than all elements in a then len(a)-1 is returned.
    If x is smaller than all elements in a then -1 is returned.
    '''
    i = bisect.bisect_right(a, x)
    return i - 1

def closest_indices(x_value, x_set, max_x_diff=None):
    '''
    Return 3 values (s, i1, i2) described below.
    
    First return value is normalized difference (0 to 1) in x_value found between two elements in x_set, which is assumed to be increasing.
    x_set is usually time. For example if x_value is 3.75 and x_set is [3, 4] then first return value will return 0.75.
    If the closest value in x_set to x_value is more than max_x_diff away then will return s=NaN. 
    If max_x_diff is None then it's treated as infinitely.
    
    Second return value is the index of x_set element right before x_value and the third is the index of the x_set element right after x_value.
    '''
    # index of element in x_set right before or equal to x_value
    i1 = find_less_than_or_equal(x_set, x_value)  
    
    if i1 < 0:
        # specified x value occurs before any x's so return first y if it's close enough.
        if max_x_diff is not None and abs(x_value - x_set[0]) > max_x_diff:
            s = float('NaN') # not close enough
        else:
            s = 0.0 # first element
        return (s, 0, 1)
    
    if i1 >= (len(x_set) - 1):
        # specified x value occurs after all x's so return last y if it's close enough.
        if max_x_diff is not None and abs(x_value - x_set[-1]) > max_x_diff:
            s = float('NaN') # not close enough
        else:
            s = 1.0 # last element
        return (s, len(x_set)-2, len(x_set)-1)
    
    # i2 is the index of the element in x_set right after x_value.
    # at this point x_set[i1] can't be equal to x_set[i2] or else
    # i2 would have been returned instead of i1 above.
    i2 = i1 + 1
    
    if x_value == x_set[i1]:
        # don't need to interpolate since match exactly.
        return (0.0, i1, i2)
    
    # Check to see if there's too large of separation in x that would make the interpolation unreliable.
    if max_x_diff is not None and abs(x_set[i1] - x_set[i2]) > max_x_diff:
        return (float('NaN'), i1, i2)
    
    s = float(x_value - x_set[i1]) / (x_set[i2] - x_set[i1])
    
    return (s, i1, i2)

def interp_list_from_set(x_value, x_set, y_set, max_x_diff=None):
    '''
    Return interpolated element in y_set corresponding to x value. Each element in y_set should be a list or tuple of values to be interpolated.
    Assumes x_set is sorted ascending.  If x_value outside bounds of x_set then returns closest value unless the distance is larger than
    max_x_diff, then will return list of NaN the same size of the element of y_set.
    x_set and y_set must have the same amounts of elements. Raise ValueError if sets aren't same size.
    '''
    if len(x_set) != len(y_set):
        raise ValueError("Sets must be same size to interpolate.")
    
    s, i1, i2 = closest_indices(x_value, x_set, max_x_diff)
    
    if math.isinf(s):
        return [float('NaN')] * len(y_set[0])
    else:  
        return [(1-s)*v0 + s*v1 for v0, v1 in zip(y_set[i1], y_set[i2])]

def interp_single_from_set(x_value, x_set, y_set, max_x_diff=None):
    '''
    Return interpolated element in y_set corresponding to x value. Each element in y_set should be a scalar value.
    Assumes x_set is sorted ascending.  If x_value outside bounds of x_set then returns closest value unless the distance is larger than
    max_x_diff, then will return NaN.
    x_set and y_set must have the same amounts of elements. Raise ValueError if sets aren't same size.
    '''
    if len(x_set) != len(y_set):
        raise ValueError("Sets must be same size to interpolate.")
    
    s, i1, i2 = closest_indices(x_value, x_set, max_x_diff)
    
    if math.isinf(s):
        return float('NaN')
    else:  
        return (1-s)*y_set[i1] + s*y_set[i2]

def interp_angle_deg_from_set(x_value, x_set, angles, max_x_diff=None):
    '''
    Return interpolated angle in 'angles' corresponding to x value and wrapped between +/- 180.  All angles should be in degrees. 
    Assumes x_set is sorted ascending.  If x_value outside bounds of x_set then returns closest angle unless the distance is larger than
    max_x_diff, then will return NaN.
    x_set and angles must have the same amounts of elements. Raise ValueError if sets aren't same size.
    '''
    if len(x_set) != len(angles):
        raise ValueError("Sets must be same size to interpolate.")
    
    s, i1, i2 = closest_indices(x_value, x_set, max_x_diff)
    
    if math.isinf(s):
        return float('NaN')
    else:  
        return wrap_angle_degrees(interp_angle_deg(angles[i1], angles[i2], s))

def interp_angle_deg(a0, a1, s):
    '''Return interpolated angle between a0 and a1 by a factor s in range[0..1]'''
 
    max_range = 360.0
    angle_diff = (a1 - a0) % max_range
    shortest_angle = 2*angle_diff % max_range - angle_diff
    return a0 + s*shortest_angle

def wrap_angle_degrees(angle):
    
    while angle <= -180:
        angle += 360
    while angle > 180:
        angle -= 360
        
    return angle

def wrap_angle_radians(angle):
    
    while angle <= -math.pi:
        angle += 2*math.pi
    while angle > math.pi:
        angle -= 2*math.pi
        
    return angle

def average(numeric_list):
    
    try:
        return float(sum(numeric_list)) / len(numeric_list)
    except ZeroDivisionError:
        return 0.0

def write_args_to_file(filename, out_directory, args):
    # Write arguments out to file for archiving purposes.
    args_filepath = os.path.join(out_directory, filename)
    with open(args_filepath, 'wb') as args_file:
        csv_writer = csv.writer(args_file)
        csv_writer.writerow(['Date', str(datetime.datetime.now())])
        csv_writer.writerows([[k, v] for k, v in args.items()])
        
def logging_string_to_level(level):
    
    level = level.lower()
    
    if level == 'debug':
        return logging.DEBUG
    if level == 'info':
        return logging.INFO
    if level == 'warn':
        return logging.WARN
    if level == 'error':
        return logging.ERROR
    if level == 'critical':
        return logging.DEBUG
    
    return None
    
def make_filename_unique(directory, fname_no_ext):
    
    original_fname = fname_no_ext
    dir_contents = os.listdir(directory)
    dir_fnames = [os.path.splitext(c)[0] for c in dir_contents]
    
    while fname_no_ext in dir_fnames:
        
        try:
            v = fname_no_ext.split('_')
            i = int(v[-1])
            i += 1
            fname_no_ext = '_'.join(v[:-1] + [unicode(i)])
        except ValueError:
            fname_no_ext = '{}_{}'.format(original_fname, 1)

    return fname_no_ext