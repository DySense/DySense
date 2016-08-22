#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import datetime
import utm

from dysense.core.csv_log import CSVLog
from dysense.processing.utility import *

class PostProcessor:
    '''Process session to calculate position/orientation of platform and every sensor measurement.'''
    
    def __init__(self, session_output, geotagger, log):
        '''Constructor'''
        self.session_output = session_output
        self.geotagger = geotagger
        self.log = log
        
        self.processed_session = None
    
    class ExitReason:
        '''Map reason for a exiting run() method to a unique ID.'''
        success = 0
        session_invalid = 1

    def run(self):
        '''
        Read in session, calculate platform pose and then use sensor offsets to geotag sensor readings.
        Return ExitReason that indicates result.  If success then can access results through processed_session field.
        '''
        if not self.session_output.session_valid:
            self.log.error("Session marked as invalid. Delete invalidated.txt before processing.")
            return PostProcessor.ExitReason.session_invalid
        
        # Read in generic session info (start time, end time, operator name, etc).
        session_info = self.session_output.read_session_info()
        
        # Determine platform position. 
        position_measurements_by_source = self.session_output.read_positions()
        
        # There could be more than one source if multiple GPS's are used (e.g. for yaw)
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
        roll_angles, pitch_angles, yaw_angles = self.session_output.read_orientations()
        
        # Detect if orientation values can be used for geotagging.
        valid_roll_angles = contains_measurements(roll_angles)
        valid_pitch_angles = contains_measurements(pitch_angles)
        valid_yaw_angles = contains_measurements(yaw_angles)
        
        # Ensure all angles are in radians and between +/- PI.
        if valid_roll_angles:
            roll_angles = standardize_to_radians(roll_angles, self.session_output.roll_source, 'roll')
        if valid_pitch_angles:
            pitch_angles = standardize_to_radians(pitch_angles, self.session_output.pitch_source, 'pitch')
        if valid_yaw_angles:
            yaw_angles = standardize_to_radians(yaw_angles, self.session_output.yaw_source, 'yaw')
        
        if not multiple_position_sensors and 'derived' in [roll_angles, pitch_angles]:
            self.log.warn("Can not derive pitch or roll unless there are multiple position sources.")
        
        if yaw_angles == 'derived':
            if multiple_position_sensors:
                raise Exception('TODO')
                valid_yaw_angles = True
            else:
                self.log.warn("Deriving yaw from single position source isn't supported yet.")
        
        # Read in sensor info and log data.
        sensors = self.session_output.get_complete_sensors()
        
        # Remove any sensors that don't have any log data since they essentially weren't used.
        sensors = [sensor for sensor in sensors if sensor['log_data'] is not None]
        
        # Go through and calculate position and orientations of all sensor measurements.
        # This will add 'position' and 'orientation' keys directly to the log elements.
        for sensor in sensors:
    
            offsets_in_radians = [angle * math.pi/180.0 for angle in sensor['orientation_offsets']]
            
            self.geotagger.tag_all_readings(sensor['log_data'], sensor['position_offsets'], offsets_in_radians,
                                       platform_positions,
                                       roll_angles if valid_roll_angles else None,
                                       pitch_angles if valid_pitch_angles else None,
                                       yaw_angles if valid_yaw_angles else None)
            
            # Keep track of how many measurements didn't match up with platform position/angles based on time-stamps.
            num_unmatched_positions = 0
            num_unmatched_roll_angles = 0
            num_unmatched_pitch_angles = 0
            num_unmatched_yaw_angles = 0
            
            # Convert angles back to degrees and positions back to lat / long.
            # Iterate over copy so we can delete data entries as we go.
            log_data_copy = sensor['log_data'][:]
            for data in log_data_copy:
                
                # Make sure sensor was assigned a position before trying to convert back to lat/lon.
                if math.isnan(data['position'][0]):
                    num_unmatched_positions += 1
                    # Measurement is only valid if it has a position.  No point in keeping it otherwise.
                    sensor['log_data'].remove(data)
                    continue 
                
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
                self.log.warn('Sensor {} ignored {} entries because they did not have a valid position to match with.'.format(sensor['sensor_id'], num_unmatched_positions))
            if valid_roll_angles and num_unmatched_roll_angles > 0:
                self.log.warn('Sensor {} could not calculate roll for {} entries.'.format(sensor['sensor_id'], num_unmatched_roll_angles))
            if valid_pitch_angles and num_unmatched_pitch_angles > 0:
                self.log.warn('Sensor {} could not calculate pitch for {} entries.'.format(sensor['sensor_id'], num_unmatched_pitch_angles))
            if valid_yaw_angles and num_unmatched_yaw_angles > 0:
                self.log.warn('Sensor {} could not calculate yaw for {} entries.'.format(sensor['sensor_id'], num_unmatched_yaw_angles))
            
        # Convert platform positions back to WGS-84.
        for position in platform_positions:
            lat, long = utm.to_latlon(position.x, position.y, zone_num, zone_letter)
            position.x = lat
            position.y = long
            
        # Convert platform positions back to degrees.
        if valid_roll_angles:
            for angle in roll_angles:
                angle.angle *= 180.0 / math.pi
        if valid_pitch_angles:
            for angle in pitch_angles:
                angle.angle *= 180.0 / math.pi
        if valid_yaw_angles:
            for angle in yaw_angles:
                angle.angle *= 180.0 / math.pi
                
        # Combine platform position and orientation so that they are measured at the same time.                
        platform_state = self.calculate_platform_state(platform_positions, roll_angles, pitch_angles, yaw_angles)
        
        # Save results so user can choose what to do with them.
        self.processed_session = {'session_info': session_info,
                                  'sensors': sensors,
                                  'platform_state': platform_state,
                                  }
        
        return True
    
    def calculate_platform_state(self, positions, roll_angles, pitch_angles, yaw_angles):
        pass

    def write_tagged_sensor_logs_to_file(self, output_path):
        
        if self.processed_session is None:
            return
        
        sensors = self.processed_session['sensors']
        start_utc = self.processed_session['session_info']['start_utc']
        
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
            
            log_data = sensor['log_data']
            out_data = [[d['time']] + list(d['position']) + list(d['orientation']) + list(d['data']) for d in log_data]
            for data_line in out_data:
                sensor_output_log.write(data_line)
