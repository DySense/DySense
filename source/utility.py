# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import subprocess
import json
import csv

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

def make_unicode(val):
    '''Return 'val' but as a unicode object. 'val' must be able to be converted to a bytestring (i.e. str).''' 
    if type(val) != unicode:
        # First convert to bytes (str) in case it was an numeric type and
        # then decode it as utf8, which will also work for ascii text.
        # If 'val' is already utf8 then the str() will have no effect and will just decode.
        return unicode(str(val), 'utf8')
    else:
        return val # already unicode so don't re-decode it.
    
def make_utf8(val):
    '''Return 'val' but as a UTF-8 encoded bytestring.''' 
    return make_unicode(val).encode('utf8')

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
