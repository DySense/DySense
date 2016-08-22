#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import copy
from collections import defaultdict

from dysense.core.utility import yaml_load_unicode, validate_type
from dysense.processing.utility import unicode_csv_reader

class StampedPosition(object):
    '''Time stamped position measurement.'''
    
    def __init__(self, utc_time, x, y, z):
        self.utc_time = utc_time
        self.x = x
        self.y = y
        self.z = z
        
class StampedAngle(object):
    '''Time stamped angle measurement.'''
    
    def __init__(self, utc_time, angle):
        self.utc_time = utc_time
        self.angle = angle

class SensorOffset(object):
    '''Offset of sensor from official platform position.'''
    
    def __init__(self, sensor_name, sensor_type, sensor_tag, x, y, z, roll, pitch, yaw):
        self.sensor_name = sensor_name
        self.sensor_type = sensor_type
        self.sensor_tag = sensor_tag
        self.x = x
        self.y = y
        self.z = z
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        
    @property
    def position(self):
        return (self.x, self.y, self.z)
    
    @property
    def orientation(self):
        return (self.roll, self.pitch, self.yaw)

class SessionOutput(object):
    '''
    Provide interface for reading different parts of a DySense session directory.
    Before using data user should verify that session_valid property is True.
    All files are assumed to be saved in UTF8 format.
    '''
    def __init__(self, session_path, log):
        '''Constructor'''
        self.session_path = session_path
        self.log = log
        
        self.sources = self._read_data_source_info()
        
        self.sensor_info_list = self._read_sensor_info()
        
    @property
    def position_file_path(self):
        return os.path.join(self.session_path, 'position.csv')
    
    @property
    def orientation_file_path(self):
        return os.path.join(self.session_path, 'orientation.csv')
    
    @property
    def session_info_file_path(self):
        return os.path.join(self.session_path, 'session_info.csv')
    
    @property
    def sensor_offset_file_path(self):
        return os.path.join(self.session_path, 'sensor_offsets.csv')
    
    @property
    def source_info_file_path(self):
        return os.path.join(self.session_path, 'source_info.yaml')

    @property
    def version_file_path(self):
        return os.path.join(self.session_path, 'version.txt')

    @property
    def sensor_info_directory_path(self):
        return os.path.join(self.session_path, 'sensor_info/')
    
    @property
    def data_logs_directory_path(self):
        return os.path.join(self.session_path, 'data_logs/')
    
    @property
    def data_files_directory_path(self):
        return os.path.join(self.session_path, 'data_files/')
    
    @property
    def time_source(self):
        return self.sources.get('time_source', None)

    @property
    def position_sources(self):
        return self.sources.get('position_sources', [])

    @property
    def roll_source(self):
        return self.sources.get('roll_source', None)
    
    @property
    def pitch_source(self):
        return self.sources.get('pitch_source', None)
    
    @property
    def yaw_source(self):
        return self.sources.get('yaw_source', None)
    
    @property
    def session_valid(self):
        return not os.path.exists(os.path.join(self.session_path, 'invalidated.txt'))
    
    def read_positions(self):
        '''
        Read time-stamped position information from platform position file. 
        
        Return dictionary of position sources found in position file where each key is the position source name and
         the value is a list of StampedPosition objects sorted by time.  
         
        If a line is missing data then it will be skipped and an error message will be logged.
        If there are no position sources than will raise ValueError
        '''
        # Make sure there is a valid position source.
        if len(self.position_sources) == 0:
            raise ValueError('No valid position sources found in session metadata.')
        
        # Dictionary that will be returned at end of method.
        measurements_by_source = defaultdict(list)

        # If we have more than 1 source then the first column will identify which source the reading is from.  
        multiple_position_sources = len(self.position_sources) > 1
                
        minimum_fields_per_row = 3 # time, x and y
        if multiple_position_sources:
            minimum_fields_per_row += 1 # plus sensor id column
        else:
            # Only have 1 position source so the ID is the same for all measurements.
            position_source_name = self.position_sources[0]['sensor_id']
                
        with open(self.position_file_path, 'rb') as position_file:
            file_reader = unicode_csv_reader(position_file)
            for line_num, line in enumerate(file_reader):
                
                # Remove blank entries and strip any whitespace from valid entries.
                line = [entry.strip() for entry in line if entry.strip() != ""]
                
                if len(line) == 0 or line[0].startswith('#'):
                    continue # blank or comment line
                
                if len(line) < minimum_fields_per_row:
                    self.log.error('Position line #{} contains only {} elements.'.format(line_num, len(line)))
                    continue
                
                if multiple_position_sources:
                    position_source_name = line[0]
                    # UTC time comes after position sensor identifier.
                    time_idx = 1
                else:
                    # UTC time is first column.  Source identifier (name) doesn't change.
                    time_idx = 0
                
                utc_time = float(line[time_idx])
                x = float(line[time_idx + 1])
                y = float(line[time_idx + 2])
                try:
                    z = float(line[time_idx + 3])
                except IndexError:
                    z = 0.0 # z is optional.
                
                new_position = StampedPosition(utc_time, x, y, z)
                
                measurements_by_source[position_source_name].append(new_position)
                
        # Sort measurements by time for each source. 
        for source_name, source_positions in measurements_by_source.iteritems():    
            measurements_by_source[source_name] = sorted(source_positions, key=lambda position: position.utc_time)
                
        return measurements_by_source
    
    def read_orientations(self):
        '''
        Read time-stamped angles from platform orientation file. 
        
        Return value will be roll, pitch, yaw where each of these may be 3 different things:
            1) None if that source (e.g. pitch source) wasn't specified for session.
            2) The string 'derived' if the angles should be calculated (e.g. using multiple-accurate position sources)
            3) A list of TimeStampedAngles sorted by time.
         
        If a line is missing data then it will be skipped and an error message will be logged.
        If no orientation file exists then all 3 return values will be None
        '''
        def read_angle(file_lines, source, angle_matches):
            
            measurements_stored = False
            if not source or source['sensor_id'].lower() == 'none':
                measurements = None
            elif source['sensor_id'].lower() == 'derived':
                measurements = 'derived'
            else:
                measurements = []
                measurements_stored = True
                
            for line_num, line in enumerate(file_lines):
                
                # Remove blank entries and strip any whitespace from valid entries.
                line = [entry.strip() for entry in line if entry.strip() != ""]
                
                if len(line) == 0 or line[0].startswith('#'):
                    continue # blank or comment line
                
                if len(line) < 3:
                    self.log.error('Orientation line #{} contains only {} elements.'.format(line_num, len(line)))
                    continue

                utc_time = float(line[0])
                angle_type = line[1]
                angle_value = float(line[2])

                if angle_type in angle_matches:
                    measurements.append(StampedAngle(utc_time, angle_value))
                
            # Sort measurements by time. 
            if measurements_stored:
                measurements = sorted(measurements, key=lambda measurement: measurement.utc_time)
                
            return measurements
        
        if not os.path.exists(self.orientation_file_path):
            roll_values = None
            pitch_values = None
            yaw_values = None
        else:
            with open(self.orientation_file_path, 'rb') as orientation_file:
                file_reader = unicode_csv_reader(orientation_file)
                file_lines = [line for line in file_reader]
                roll_values = read_angle(file_lines, self.roll_source, ['r', 'roll'])
                pitch_values = read_angle(file_lines, self.pitch_source, ['p', 'pitch'])
                yaw_values = read_angle(file_lines, self.yaw_source, ['y', 'yaw'])
    
        return roll_values, pitch_values, yaw_values
    
    def read_session_info(self):
        
        session_info = {}
        with open(self.session_info_file_path, 'r') as session_info_file:
            file_reader = unicode_csv_reader(session_info_file)
            for line_num, line in enumerate(file_reader):
                
                if len(line) == 0 or line[0].strip().startswith('#'):
                    continue # blank or comment line
                
                info_name = line[0]
                try:
                    info_value = line[1]
                except IndexError:
                    info_value = None
                
                # Convert information that should be floats.
                if info_name in ['start_utc', 'end_utc', 'start_sys_time', 'end_sys_time']:
                    info_value = float(info_value)

                # Convert information that should be boolean.
                if info_name in ['surveyed']:
                    info_value = bool(info_value)
                
                session_info[info_name] = info_value
                
        return session_info
    
    def read_metadata_version(self):
        
        with open(self.version_file_path, 'r') as version_file:
            return unicode(version_file.readline(), 'utf-8')
        
    def get_complete_sensors(self):
        
        # Initialize sensors with information from sensor info yaml files.
        sensors = copy.deepcopy(self.sensor_info_list)
        
        # Combine log data with sensor info.
        for sensor in sensors:
            try:
                log_data, log_file_name = self._read_sensor_log_data(sensor)

            except Exception as e:
                self.log.error('Cannot read log for {} - reason: {}'.format(sensor['sensor_id'], str(e)))
                log_data = None
                log_file_name = None
            
            sensor['log_data'] = log_data
            sensor['log_file_name'] = log_file_name
            
        return sensors
        
    def _read_data_source_info(self):

        with open(self.source_info_file_path, 'r') as stream:
            return yaml_load_unicode(stream)
        
    def _read_sensor_info(self):
        
        sensor_info_list = []
        for file_name in os.listdir(self.sensor_info_directory_path):
            extension = os.path.splitext(file_name)[1]
            if 'yaml' not in extension:
                continue
            
            file_path = os.path.join(self.sensor_info_directory_path, file_name)
            with open(file_path, 'r') as stream:
                sensor_info = yaml_load_unicode(stream)
            
            sensor_info_list.append(sensor_info)
            
        return sensor_info_list
    
    def _read_sensor_log_data(self, sensor_info):
        '''Don't call this directly.  Instead use '''
        
        # The beginning part of the filename that we expect based on provided sensor info.
        log_file_name_start = '{}_{}_{}'.format(sensor_info['sensor_id'], sensor_info['instrument_type'], sensor_info['instrument_tag'])
        
        matching_file_names = [] 
        for fname in os.listdir(self.data_logs_directory_path):
            file_name_without_ext, extension = os.path.splitext(fname)
            if log_file_name_start in fname and 'csv' in extension:
                matching_file_names.append(fname)
            
        if len(matching_file_names) == 0:
            raise Exception("No matching log starting with {}".format(log_file_name_start))
        elif len(matching_file_names) > 1:
            raise Exception("More than one log starting with {}".format(log_file_name_start))
        else:
            matching_file_name = matching_file_names[0]
        
        # Look up what types line up which pieces of data.
        if sensor_info['metadata'] is None:
            raise Exception("Cannot convert sensor data since no metadata could be found.")
            
        conversion_types = [setting_metadata['type'] for setting_metadata in sensor_info['metadata']['data']]

        file_path = os.path.join(self.data_logs_directory_path, matching_file_name)
        
        sensor_log_data = []
        with open(file_path, 'rb') as log_file:
            file_reader = unicode_csv_reader(log_file)
            for line_num, line in enumerate(file_reader):
                
                if len(line) == 0:
                    continue # blank
                
                # UTC time is always first column.
                time_entry = line[0].strip()
                
                if time_entry == "" or time_entry.startswith('#'):
                    continue # invalid or comment line

                utc_time = float(time_entry)
                
                log_data_entry = line[1:]
                
                # Convert each piece of data to the correct type.
                for element_idx, element_value in enumerate(log_data_entry):
                    try:
                        log_data_entry[element_idx] = validate_type(element_value, conversion_types[element_idx])
                    except ValueError:
                        raise ValueError("{} cannot be converted into the expected type '{}'".format(element_value, conversion_types[element_idx]))

                sensor_log_data.append({'time': utc_time, 'data': log_data_entry})
                
        # Sort data by time stamp.
        sensor_log_data = sorted(sensor_log_data, key=lambda data: data['time'])
                
        return sensor_log_data, matching_file_name
        
def main():

    session_path = r'C:/Users\Kyle\dysense_session字字\HSKY_25256_20160524_190408'

    dysense_reader = SessionOutput(session_path)
    
    position_measurements_by_source = dysense_reader.read_positions()
    
    for sensor_name, position_measurements in position_measurements_by_source.iteritems():
        print '{} - {} positions'.format(sensor_name, len(position_measurements))
        
    roll_values, pitch_values, yaw_values = dysense_reader.read_orientations()
    
    print 'roll - {}'.format(roll_values)
    print 'pitch - {}'.format(pitch_values)
    print 'yaw - {}'.format(yaw_values)
    
    for value in yaw_values:
        print '{} - {}'.format(repr(value.utc_time), value.angle)

    sensors = dysense_reader.get_complete_sensors()
    for sensor in sensors:
        print sensor
        
    metadata_version = dysense_reader.read_metadata_version()
    print 'metadata version ' + metadata_version

if __name__ == '__main__':
    main()
    

