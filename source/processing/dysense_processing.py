#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
import os
import csv
import argparse
import math
import datetime
import time
import utm
import copy

from postprocessing.dysense_reader import DySenseReader
from postprocessing.geotag import GeoTagger
from source.utility import decode_command_line_arg, wrap_angle_radians
from source.csv_log import CSVLog

def postprocess(**args):
    
    # Copy args so we can archive them to a file when function is finished.
    args_copy = args.copy()
    
    # Convert arguments to local variables of the correct type. Decode strings to unicode.
    #session_directory_path = decode_command_line_arg(args.pop('session_directory'))
    session_directory_path = args.pop('session_directory')
    
    if len(args) > 0:
        print "Unexpected arguments provided: {}".format(args)
        return -1 # ExitReason.bad_arguments
    
    dysense_reader = DySenseReader(session_directory_path)
    
    # TODO make max time diff a command arg
    geotagger = GeoTagger(max_time_diff=1)
    
    if not dysense_reader.session_valid:
        print "Session marked as invalid. Delete invalidated.txt before processing."
        return -1 # ExitReason.session_invalid
    
    # First read in generic session info.
    session_info = dysense_reader.read_session_info()
    
    # First determine platform position.
    position_measurements_by_source = dysense_reader.read_positions()
    
    multiple_position_sensors = len(position_measurements_by_source) > 1
    
    if multiple_position_sensors:
        # Need to combine all sources into a single sequence of platform positions.
        raise Exception("TODO")
    else:
        platform_positions = position_measurements_by_source.values()[0]
        
    # Convert positions to UTM so we can geo-reference sensor measurements.
    # This assumes that stored positions were in WGS-84 Lat/Long. 
    # TODO: consider just using local coordinates to avoid any distortion or zone issues with UTM.
    # TODO: if stick with UTM then should verify zone is consistent.
    for position in platform_positions:
        easting, northing, zone_num, zone_letter = utm.from_latlon(position.x, position.y)
        position.x = easting
        position.y = northing
    
    # Determine platform orientation, possibly derived from position source(s).
    roll_angles, pitch_angles, yaw_angles = dysense_reader.read_orientations()
    
    # Detect if orientation values can be used for geotagging.
    valid_roll_angles = contains_measurements(roll_angles)
    valid_pitch_angles = contains_measurements(pitch_angles)
    valid_yaw_angles = contains_measurements(yaw_angles)
    
    # Ensure all angles are in radians and between +/- PI.
    if valid_roll_angles:
        roll_angles = standardize_to_radians(roll_angles, dysense_reader.roll_source, 'roll')
    if valid_pitch_angles:
        pitch_angles = standardize_to_radians(pitch_angles, dysense_reader.pitch_source, 'pitch')
    if valid_yaw_angles:
        yaw_angles = standardize_to_radians(yaw_angles, dysense_reader.yaw_source, 'yaw')
    
    if not multiple_position_sensors and 'derived' in [roll_angles, pitch_angles]:
        print "WARNING - can not derive pitch or roll unless there are multiple position sources."
    
    if yaw_angles == 'derived':
        if multiple_position_sensors:
            raise Exception('TODO')
        else:
            print "WARNING - Deriving yaw from single position source isn't supported yet."
    
    # Read in sensor info and log data.
    sensors = dysense_reader.get_complete_sensors()
    
    # Remove any sensors that don't have any log data since they essentially weren't used.
    sensors = [sensor for sensor in sensors if sensor['log_data'] is not None]
    
    # Go through and calculate position and orientations of all sensor measurements.
    # This will add 'position' and 'orientation' keys directly to the log elements.
    for sensor in sensors:

        offsets_in_radians = [angle * math.pi/180.0 for angle in sensor['orientation_offsets']]
        
        geotagger.tag_all_readings(sensor['log_data'], sensor['position_offsets'], offsets_in_radians,
                                   platform_positions,
                                   roll_angles if valid_roll_angles else None,
                                   pitch_angles if valid_pitch_angles else None,
                                   yaw_angles if valid_yaw_angles else None)
        
        # Keep track of how many measurements didn't match up with platform position/angles.
        # If angles don't match up then that will show up as unmatched 
        num_unmatched_positions = 0
        num_unmatched_roll_angles = 0
        num_unmatched_pitch_angles = 0
        num_unmatched_yaw_angles = 0
        
        # Convert angles back to degrees and positions back to lat / long
        for data in sensor['log_data']:
            
            # Make sure sensor was assigned a position before trying to convert back to lat/lon.
            # TODO delete measurement?? 
            sdfklj
            if math.isnan(data['position'][0]):
                num_unmatched_positions += 1
                continue # measurement is only valid if it has a position.
            
            lat, long = utm.to_latlon(data['position'][0], data['position'][1], zone_num, zone_letter)
            data['position'] = (lat, long, data['position'][2])
            
            roll = data['orientation'][0] * 180.0 / math.pi
            pitch = data['orientation'][1] * 180.0 / math.pi
            yaw = data['orientation'][2] * 180.0 / math.pi
            
            data['orientation'] = (roll, pitch, yaw)
                
            # These angles might all be NaN if there wasn't a source for them.  In that case it's normal to have them all unmatched.
            if math.isnan(roll):
                num_unmatched_roll_angles += 1
            if math.isnan(pitch):
                num_unmatched_pitch_angles += 1
            if math.isnan(yaw):
                num_unmatched_yaw_angles += 1

        # Warn user if any sensor measurement times didn't match up close enough to platform position/angles. 
        if num_unmatched_positions > 0:
            print 'WARNING - sensor {} ignored {} entries because they did not have a valid position.'.format(sensor['sensor_id'], num_unmatched_positions)
        if valid_roll_angles and num_unmatched_roll_angles > 0:
            print 'WARNING - sensor {} could not calculate roll for {} entries.'.format(sensor['sensor_id'], num_unmatched_roll_angles)
        if valid_pitch_angles and num_unmatched_pitch_angles > 0:
            print 'WARNING - sensor {} could not calculate pitch for {} entries.'.format(sensor['sensor_id'], num_unmatched_pitch_angles)
        if valid_yaw_angles and num_unmatched_yaw_angles > 0:
            print 'WARNING - sensor {} could not calculate yaw for {} entries.'.format(sensor['sensor_id'], num_unmatched_yaw_angles)   
        
    # Convert platform positions back to WGS-84.
    for position in platform_positions:
        lat, long = utm.to_latlon(position.x, position.y, zone_num, zone_letter)
        position.x = lat
        position.y = long
        
    # Convert back to degrees.
    if valid_roll_angles:
        for angle in roll_angles:
            angle.angle *= 180.0 / math.pi
    if valid_pitch_angles:
        for angle in pitch_angles:
            angle.angle *= 180.0 / math.pi
    if valid_yaw_angles:
        for angle in yaw_angles:
            angle.angle *= 180.0 / math.pi 
        
    # TODO make this optional
    write_tagged_sensor_logs_to_file(sensors, session_directory_path, session_info)
    
    #write_platform_state_to_file(platform_positions, roll_angles, pitch_angles, yaw_angles)
    
    # TODO could also upload to database
    
    
def calculate_platform_state():
    
    pass

def standardize_to_radians(angles, source, angle_type):

    # Set to false if already in radians.
    need_to_convert = True
    
    try:
        units = orientation_source_units(source)
        
        if is_radians(units):
            need_to_convert = False # already in radians
        if not is_degrees(units):
            print '{} units \'{}\' is not recognized. Assuming degrees.'.format(angle_type.title(), units)
        
    except KeyError:
        print 'Units not listed for {} source. Assuming degrees.'.format(angle_type)

    if need_to_convert:
        # Make a copy so we don't modify the original.
        angles = copy.copy(angles)
        for angle in angles:
            angle.angle *= math.pi / 180.0

    # Temporary debug output
    if need_to_convert:
        print 'Converting {} angles to radians for geotagging.'.format(angle_type)
    else:
        print '{} angles already in radians for geotagging.'.format(angle_type.title())
        
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

def write_tagged_sensor_logs_to_file(sensors, session_directory_path, session_info):
    
    formatted_time = datetime.datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")
    processed_directory_name = 'results_' + formatted_time
    processed_directory_path = os.path.join(session_directory_path, 'processed', processed_directory_name)
    os.makedirs(processed_directory_path)
    
    tagged_logs_directory_path = os.path.join(processed_directory_path, 'tagged_logs')
    os.makedirs(tagged_logs_directory_path)
    
    for sensor in sensors:
        
        formatted_session_start_time = datetime.datetime.fromtimestamp(session_info['start_utc']).strftime("%Y%m%d_%H%M%S")
        sensor_log_file_name = "{}_{}_{}_{}_{}.csv".format(sensor['sensor_id'],
                                                           sensor['instrument_type'],
                                                           sensor['instrument_tag'],
                                                           formatted_session_start_time,
                                                          'tagged')
        
        sensor_log_file_path = os.path.join(tagged_logs_directory_path, sensor_log_file_name)
        sensor_output_log = CSVLog(sensor_log_file_path, 1)
        
        log_data = sensor['log_data']
        out_data = [[d['time']] + list(d['position']) + list(d['orientation']) + list(d['data']) for d in log_data]
        for data_line in out_data:
            sensor_output_log.write(data_line)

def contains_measurements(lst):
    
    return isinstance(lst, (list, tuple)) and len(lst) > 0
    
if __name__ == '__main__':
    ''''''

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('session_directory', help='DySense session directory.')
    #parser.add_argument('-cm', dest='code_modifications_filepath', default='none',  help='Filepath to modifications CSV file to add, delete, change existing codes.')

    # Convert namespace to dictionary.
    args = vars(parser.parse_args())
    
    #args = {'session_directory': r'L:\sunflower\PCRT_20160001_20160614_020826'}
    
    exit_code = postprocess(**args)
    
    #if exit_code == ExitReason.bad_arguments:
    #    print "\nSee --help for argument descriptions."
    
    sys.exit(exit_code)
