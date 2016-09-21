#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
import os
import argparse
import datetime
import time

from dysense.processing.dysense_output import SessionOutputFactory
from dysense.processing.geotagger import GeoTagger
from dysense.processing.database import Database
from dysense.processing.post_processor import PostProcessor
from dysense.processing.platform_state import filter_down_platform_state
from dysense.processing.log import setup_logging, log
from dysense.core.utility import write_args_to_file, decode_command_line_arg
from dysense.core.utility import logging_string_to_level
from dysense.core.csv_log import CSVLog

def main():
    '''
    Process output of the DySense program and optionally upload results to the database. 
    Save files in a sub-directory of the session output folder. 
    '''
    parser = argparse.ArgumentParser(description=main.__doc__)
    
    # Required (positional) arguments
    parser.add_argument('session_directory', help='Path to DySense output session directory.')
    
    # Optional arguments
    parser.add_argument('-u', dest='upload_to_database', default='true',  help='If true then will upload results to database. Default true.')
    parser.add_argument('-r', dest='max_platform_rate', default=5,  help='Set this rate (in Hz) to limit the amount of platform state data that will be loaded into database. Default 5 Hz. If <= 0 then will store all data.')
    parser.add_argument('-m', dest='max_time_diff', default=1, help='Will only match sensor readings to a platform position/orientation if the difference in time '
                        '(in seconds) is less than this value. Default is 1 second.')
    parser.add_argument('-c', dest='console_log_level', default='info',  help='Either debug, info, warn, error, critical or none to disable. Default is info.')
    parser.add_argument('-f', dest='file_log_level', default='info',  help='Either debug, info, warn, error, critical. Default is info.')

    # Convert namespace to dictionary.
    args = vars(parser.parse_args())
    
    postprocess(**args)
    
    sys.exit(0)

def postprocess(**args):
    '''
    Calculate platform state, geotag sensor data and optionally upload results to database.
    Arguments should follow command line formatting (e.g. boolean as string 'true' instead of True)
    Return processed session or None if error occurs.
    '''
    # Copy args so we can archive them to a file when function is finished.
    args_copy = args.copy()
    
    # Convert arguments to local variables of the correct type. Decode strings to unicode.
    session_directory_path = decode_command_line_arg(args.pop('session_directory'))
    file_log_level = logging_string_to_level(decode_command_line_arg(args.pop('file_log_level')))
    console_log_level = logging_string_to_level(decode_command_line_arg(args.pop('console_log_level')))
    max_time_diff = float(args.pop('max_time_diff'))
    max_platform_rate = float(args.pop('max_platform_rate'))
    upload_to_database = decode_command_line_arg(args.pop('upload_to_database')).lower() == 'true'
    
    if len(args) > 0:
        raise ValueError("Unexpected arguments provided: {}".format(args))
    
    if file_log_level is None:
        raise ValueError('Invalid value for file_log_level')
    
    processed_directory_path = create_output_directory(session_directory_path)
    
    setup_logging(processed_directory_path, file_log_level, console_log_level)
    
    # Determine SessionOutput type based on the output format version.
    session_output = SessionOutputFactory.get_object(session_directory_path)
    
    if session_output is None:
        return None
    
    geotagger = GeoTagger(max_time_diff)
    processor = PostProcessor(session_output, geotagger, max_time_diff)
    
    # Use processor to conceptually convert SessionOutput into a dictionary ('processed_session')
    # that can be written out to CSV files or uploaded to the database.
    result = processor.run()
    
    if result != PostProcessor.ExitReason.success:
        log().critical("Processing failed.")
        return None
    
    write_tagged_sensor_logs_to_file(processed_directory_path, processor.processed_session)
    write_platform_state_to_file(processed_directory_path, processor.processed_session)
    
    # Archive arguments in case we need to reference them in the future.
    write_args_to_file('arguments.csv', processed_directory_path, args_copy)
    
    if upload_to_database:
        filter_down_platform_state(processor.processed_session, max_platform_rate)
        # TODO don't pass log(), but use it directly in Database class once Mark is finished.
        database = Database(log())
        upload_success = database.upload(processor.processed_session)
    
    log().info('Results are in {}/'.format(os.path.basename(os.path.normpath((processed_directory_path)))))
    log().info('Finished')
    
    return processor.processed_session
    
def create_output_directory(session_directory_path):
    '''Create sub-directory to hold any files associated with this post processing run. Return new output path.'''
    
    formatted_time = datetime.datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")
    processed_directory_name = 'processed_' + formatted_time
    processed_directory_path = os.path.join(session_directory_path, 'processed', processed_directory_name)
    os.makedirs(processed_directory_path)
    
    return processed_directory_path
 
def write_tagged_sensor_logs_to_file(output_path, processed_session):
    '''Write sensor data + state out to individual CSV log files at the specified path.'''
    
    sensors = processed_session['sensors']
    start_utc = processed_session['session_info']['start_utc']
    
    tagged_logs_directory_path = os.path.join(output_path, 'tagged_logs')
    os.makedirs(tagged_logs_directory_path)
    
    for sensor in sensors:
        
        formatted_session_start_time = datetime.datetime.fromtimestamp(start_utc).strftime("%Y%m%d_%H%M%S")
        sensor_log_file_name = "{}_{}_{}_{}_{}.csv".format(sensor['sensor_id'],
                                                           sensor['instrument_type'],
                                                           sensor['instrument_tag'],
                                                           formatted_session_start_time,
                                                          'tagged')
        
        sensor_log_file_path = os.path.join(tagged_logs_directory_path, sensor_log_file_name)
        sensor_output_log = CSVLog(sensor_log_file_path, 1)
        
        sensor_data_names = [setting['name'] for setting in sensor['metadata']['data']]
        sensor_output_log.handle_metadata(['utc_time', 'latitude', 'longitude', 'altitude', 'roll', 'pitch', 'yaw', 'height'] + sensor_data_names)
        
        log_data = sensor['log_data']
        out_data = [[d['time']] + list(d['state'].position) + list(d['state'].orientation) + [d['state'].height_above_ground] + list(d['data']) for d in log_data]
        for data_line in out_data:
            sensor_output_log.write(data_line)
            
def write_platform_state_to_file(output_path, processed_session):
    '''Write platform state to CSV file at the specified output path.'''
    
    platform_states = processed_session['platform_states']
    start_utc = processed_session['session_info']['start_utc']
    
    formatted_session_start_time = datetime.datetime.fromtimestamp(start_utc).strftime("%Y%m%d_%H%M%S")
    file_name = "platform_state_{}.csv".format(formatted_session_start_time)
    
    file_path = os.path.join(output_path, file_name)
    sensor_output_log = CSVLog(file_path, 1)
    
    sensor_output_log.handle_metadata(['utc_time', 'latitude', 'longitude', 'altitude', 'roll', 'pitch', 'yaw', 'height'])
    
    out_data = [[s.utc_time] + list(s.position) + list(s.orientation) + [s.height_above_ground] for s in platform_states]
    for data_line in out_data:
        sensor_output_log.write(data_line)
 
if __name__ == '__main__':
    
    main()

