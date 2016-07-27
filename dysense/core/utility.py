# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import subprocess
import json
import csv
import bisect
import math
from decimal import Decimal

def find_last_index(list_to_search, element):
    try:
        return (len(list_to_search) - 1) - list_to_search[::-1].index(element)
    except ValueError:
        return -1 # element not found at all
    
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
    '''Return value cast to expected type, or if cast is invalid than raise ValueError'''
    
    expected_type = expected_type.lower()

    if expected_type in ['int', 'integer']:
        value = int(value)
    elif expected_type in ['str', 'string']:
        value = unicode(value)
    elif expected_type in ['float', 'double']:
        value = float(value)
    elif expected_type in ['bool', 'boolean']:
        if unicode(value).lower() in ['true', 'yes', 't', 'y']:
            value = True
        elif unicode(value).lower() in ['false', 'no', 'f', 'n']:
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

def closest_value(x_value, x_set, y_set, i1=None, max_x_diff=None):
    '''
    Return y corresponding to x_value such that it matches with the closest value in x_set. 
    If i1 isn't None then it's treated as the rightmost index in x_set where x_set[i1] is less than or equal to x_value.
    If max_x_diff is specified then if the difference between x_value and the closest value in x_set exceeds this value then
    return NaN (not a number). Return None on failure.  
    '''
    if len(x_set) != len(y_set):
        return None
    
    if i1 is None:
        # index of element in x_set right before or equal to x_value
        i1 = find_less_than_or_equal(x_set, x_value)  
    
    if i1 < 0:
        # specified x value occurs before any x's so return first y if it's close enough.
        if max_x_diff is not None and abs(x_value - x_set[0]) > max_x_diff:
            return float('nan')
        else:
            return y_set[0]
    
    if i1 >= (len(x_set) - 1):
        # specified x value occurs after all x's so return last y if it's close enough.
        if max_x_diff is not None and abs(x_value - x_set[-1]) > max_x_diff:
            return float('nan')
        else:
            return y_set[-1]
    
    # i2 is the index of the element in x_set right after x_value.
    i2 = i1 + 1
    
    # Find the magnitude difference between specified x value and 2 closest values in x set.
    i1_mag = abs(x_set[i1] - x_value)
    i2_mag = abs(x_set[i2] - x_value)
    
    closest_index = i1 if (i1_mag < i2_mag) else i2
    
    # Make sure closest index is close enough to x_value to be reliable.
    if max_x_diff is not None and abs(x_set[closest_index] - x_value) > max_x_diff:
        return float('nan')
    
    return y_set[closest_index]

def interpolate(x_value, x_set, y_set, i1=None, max_x_diff=None):
    '''
    Return y value corresponding to x value.  If outside bounds of x_set then returns closest value.
    x_set and y_set must have the same amounts of elements. If i1 isn't None then it's treated as the
    rightmost index in x_set where x_set[i1] is less than or equal to x_value.  If max_x_diff is specified
    then if abs(x_set[i1] - x_set[i2]) exceeds this value OR if x_value is outside x_set and the closest value 
    is outside max_x_diff away then NaN (not a number) is returned. Return None on failure.
    '''
    if len(x_set) != len(y_set):
        return None
    
    if i1 is None:
        # index of element in x_set right before or equal to x_value
        i1 = find_less_than_or_equal(x_set, x_value)  
    
    if i1 < 0:
        # specified x value occurs before any x's so return first y if it's close enough.
        if max_x_diff is not None and abs(x_value - x_set[0]) > max_x_diff:
            return float('nan')
        else:
            return y_set[0]
    
    if i1 >= (len(x_set) - 1):
        # specified x value occurs after all x's so return last y if it's close enough.
        if max_x_diff is not None and abs(x_value - x_set[-1]) > max_x_diff:
            return float('nan')
        else:
            return y_set[-1]
    
    if x_value == x_set[i1]:
        # don't need to interpolate since match exactly.
        return y_set[i1] 
    
    # i2 is the index of the element in x_set right after x_value.
    # at this point x_set[i1] can't be equal to x_set[i2] or else
    # i2 would have been returned instead of i1 above.
    i2 = i1 + 1
    
    # Check to see if there's too large of separation in x that would make the interpolation unreliable.
    if max_x_diff is not None and abs(x_set[i1] - x_set[i2]) > max_x_diff:
        return float('nan')
    
    slope = (y_set[i2] - y_set[i1]) / (x_set[i2] - x_set[i1])
    
    return y_set[i1] + slope * (x_value - x_set[i1])

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
    