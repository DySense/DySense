import os
import sys
import subprocess

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
        value = str(value)
    elif expected_type in ['float', 'double']:
        value = float(value)
    elif expected_type in ['bool', 'boolean']:
        if str(value).lower() in ['true', 'yes', 't', 'y']:
            value = True
        elif str(value).lower() in ['false', 'no', 'f', 'n']:
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
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', out_directory])
    else:
        try:
            subprocess.Popen(['xdg-open', out_directory])
        except OSError:
            pass # can't open

