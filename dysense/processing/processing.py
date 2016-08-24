#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
import os
import argparse
import datetime
import time
import logging

from dysense.processing.dysense_output import SessionOutputFactory
from dysense.processing.geotagger import GeoTagger
from dysense.processing.utility import *
from dysense.processing.database import Database
from dysense.processing.post_processor import PostProcessor
from dysense.core.utility import write_args_to_file, decode_command_line_arg
from dysense.core.utility import logging_string_to_level

def main():
    '''Process output of DySense program and upload results to the database.'''
    
    parser = argparse.ArgumentParser(description=main.__doc__)
    
    # Required (positional) arguments
    parser.add_argument('session_directory', help='Path to DySense output session directory.')
    
    # Optional arguments
    parser.add_argument('-u', dest='upload_to_database', default='true',  help='If true then will upload results to database. Default true.')
    parser.add_argument('-m', dest='max_time_diff', default=1, help='Will only match sensor readings to a platform position/orientation if the difference in time '
                        '(in seconds) is less than this value. Default is 1 second.')
    parser.add_argument('-c', dest='console_log_level', default='none',  help='Either debug, info, warn, error, critical or none to disable. Default is info.')
    parser.add_argument('-f', dest='file_log_level', default='info',  help='Either debug, info, warn, error, critical. Default is info.')

    # Convert namespace to dictionary.
    args = vars(parser.parse_args())
    
    postprocess(**args)
    
    sys.exit(0)

def postprocess(**args):
    '''
    Calculate platform position/orientation, geotag sensor data and optionally upload results to database.
    Arguments should follow command line formatting (e.g. boolean as string 'true' instead of True)
    Return processed session or None if error occurs.
    '''
    # Copy args so we can archive them to a file when function is finished.
    args_copy = args.copy()
    
    # Convert arguments to local variables of the correct type. Decode strings to unicode.
    session_directory_path = decode_command_line_arg(args.pop('session_directory'))
    file_log_level = logging_string_to_level(decode_command_line_arg(args.pop('file_log_level')))
    console_log_level = logging_string_to_level(decode_command_line_arg(args.pop('console_log_level')))
    max_time_diff = args.pop('max_time_diff')
    upload_to_database = decode_command_line_arg(args.pop('upload_to_database')).lower() == 'true'
    
    if len(args) > 0:
        raise ValueError("Unexpected arguments provided: {}".format(args))
    
    if file_log_level is None:
        raise ValueError('Invalid value for file_log_level')
    
    processed_directory_path = create_output_directory(session_directory_path)
    
    log = setup_logging(processed_directory_path, file_log_level, console_log_level)
    
    # Setup and run post-processor to geotag sensor readings.
    session_output = SessionOutputFactory.get_object(session_directory_path, log)
    
    if session_output is None:
        return None
    
    geotagger = GeoTagger(max_time_diff, log)
    processor = PostProcessor(session_output, geotagger, log)
    
    processed_session = processor.run()
    
    # Create sensor data logs that now include position/orientation.
    processor.write_tagged_sensor_logs_to_file(processed_directory_path)
    
    # Archive arguments in case we need to reference them in the future.
    write_args_to_file('arguments.csv', processed_directory_path, args_copy)
    
    if upload_to_database:
        database_connection = None # DatabaseConnection() TODO
        upload_session_to_database(processed_session, database_connection)
    
    log.info('Results are in {}/'.format(os.path.basename(os.path.normpath((processed_directory_path)))))
    log.info('Finished')
    
    return processed_session

def upload_session_to_database(processed_session, database_connection):
    '''Return true if session is successfully uploaded.'''
    
    database = Database(database_connection)
    success = database.upload(processed_session)
    
    return success
    
def create_output_directory(session_directory_path):
    '''Create sub-directory to hold any files associated with this post processing run. Return new output path.'''
    
    formatted_time = datetime.datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")
    processed_directory_name = 'processed_' + formatted_time
    processed_directory_path = os.path.join(session_directory_path, 'processed', processed_directory_name)
    os.makedirs(processed_directory_path)
    
    return processed_directory_path
    
def setup_logging(output_path, file_log_level, console_log_level):
    '''Setup logging. Always to log file, optionally to command line if console_level isn't None. Return log.'''
    
    log = logging.getLogger("processing")
    log.setLevel(logging.DEBUG)
    handler = logging.FileHandler(os.path.join(output_path, time.strftime("processing.log")))
    handler.setLevel(file_log_level)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-5.5s]  %(message)s'))
    log.addHandler(handler)
    
    if console_log_level is not None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(console_log_level)
        handler.setFormatter(logging.Formatter('[%(levelname)-5.5s] %(message)s'))
        log.addHandler(handler)
        
    return log
 
if __name__ == '__main__':
    
    main()

