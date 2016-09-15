# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import numpy as np

from collections import defaultdict

from dysense.processing.utility import standardize_to_degrees, standardize_to_meters, contains_measurements
from dysense.processing.utility import StampedPosition, StampedAngle, ObjectState, wrap_angle_degrees, sensor_units
from dysense.core.utility import interpolate, interpolate_single, closest_value

class PostProcessor(object):
    '''
    Process session to calculate state of platform and every sensor measurement.
    This functionality is represented by a single public run() method.
    A new instance of this class should be created for each session to be processed.  
    '''
    def __init__(self, session_output, geotagger, max_time_diff, log):
        '''Constructor'''
        
        self.session_output = session_output
        self.geotagger = geotagger
        self.max_time_diff = max_time_diff
        self.log = log
        
        # Default values related to platform state that are calculated from session output.
        self.multiple_platform_positions = False
        self.platform_postitions = None
        self.platform_postition_offset = None
        self.synced_platform_positions = None
        self.roll_angles = None
        self.pitch_angles = None
        self.yaw_angles = None
        self.heights = None
        self.fixed_height = None
        
        # This will the hold the final results.
        self.processed_session = None
    
    class ExitReason:
        '''Map reason for a exiting run() method to a unique ID.'''
        
        success = 0
        session_invalid = 1
        no_platform_states = 2

    def run(self):
        '''
        Read in session, calculate platform states and then use sensor offsets to geotag sensor readings.
        Return ExitReason that indicates result.  If success then can access results through processed_session field.
        In general angles are stored in degrees and distances in meters.  If an angle is converted to radians it should
        be postfixed with _rad (e.g. roll_angle_rad)
        '''
        if not self.session_output.session_valid:
            self.log.error("Session marked as invalid. Delete invalidated.txt before processing.")
            return PostProcessor.ExitReason.session_invalid
        
        # Read in generic session info (start time, end time, operator name, etc).
        session_info = self.session_output.read_session_info()
        
        # Determine different components of platform state from the session output.
        # These methods store results as class fields since there's a lot of dependency between them,
        # and it would get messy to pass everything around as local references.
        self._calculate_platform_positions()
        self._calculate_platform_orientation()
        self._calculate_platform_height()
                
        # Determine platform state at common time stamps.  
        platform_states = self._calculate_platform_state()
        
        if len(platform_states) == 0:
            self.log.critical("No platform states could be calculated.")
            return self.ExitReason.no_platform_states
        
        # Read in sensor log data and use the time stamp of each entry to associate it with state of the sensor.
        sensors = self.session_output.get_complete_sensors()
        sensors = self._calculate_sensor_states(sensors, platform_states)
            
        # Save results so user can choose what to do with them.
        self.processed_session = {'session_info': session_info,
                                  'sensors': sensors,
                                  'platform_states': platform_states,
                                  }
        
        return PostProcessor.ExitReason.success
    
    def _calculate_platform_positions(self):
        '''Read in position measurements and average into a single sequence of positions (if multiple sensors)'''
        
        position_measurements_by_source = self.session_output.read_positions()
        
        # There could be more than one source if multiple GPS's are used (e.g. for yaw)
        self.multiple_position_sensors = len(position_measurements_by_source) > 1
        
        if self.multiple_position_sensors:
            # First need to get all positions to be relative to the same time stamps.
            self.synced_platform_positions = self._sync_platform_positions(position_measurements_by_source)
            self.synced_platform_positions = self._remove_unmatched_positions(self.synced_platform_positions)
            
            # Average positions and account for platform offset which is the difference between the
            # platform origin (0,0,0) and the averaged position.  
            self.platform_positions = self._average_platform_positions(self.synced_platform_positions)
            self.platform_position_offsets = [source['position_offsets'] for source in self.session_output.position_sources_info]
            self.platform_position_offset = np.mean(self.platform_position_offsets, axis=0)
        else:
            # Only one position source so use it directly.
            self.platform_positions = position_measurements_by_source.values()[0]
            self.platform_position_offset = self.session_output.position_sources_info[0]['position_offsets']
    
    def _calculate_platform_orientation(self):
        '''Read in Euler angles from sensors and optionally derive them from position sources.'''
        
        orientation_angles = self.session_output.read_orientations()
        self.roll_angles = orientation_angles[0]
        self.pitch_angles = orientation_angles[1]
        self.yaw_angles = orientation_angles[2]
        
        self._standardize_angles()
        self._derive_angles()
    
    def _standardize_angles(self):
        '''Ensure all platform Euler angles are in degrees and between +/- 180.'''
    
        self.roll_angles = self._standardize_angle(self.roll_angles, self.session_output.roll_source, 'roll')
        self.pitch_angles = self._standardize_angle(self.pitch_angles, self.session_output.pitch_source, 'pitch')
        self.yaw_angles = self._standardize_angle(self.yaw_angles, self.session_output.yaw_source, 'yaw')
        
    def _standardize_angle(self, angles, source, angle_type):
        '''Return updated list of angles for the specified source that are in degrees and between +/- 180'''
        
        if contains_measurements(angles):
            sensor_info = self.session_output.find_matching_sensor_info(source)
            try:
                units = sensor_units(sensor_info, source['orientation_index'])
            except:
                self.log.warn('Units not listed for {} source. Assuming degrees.'.format(angle_type))
                units = 'degrees'
            angles = standardize_to_degrees(angles, units, angle_type)
            
        return angles
        
    def _derive_angles(self):
        '''Use platform position source(s) to calculate any Euler angle marked as "derived"'''
        
        if self.roll_angles == 'derived':
            self.roll_angles = self._derive_roll_angles()
        if self.pitch_angles == 'derived':
            self.pitch_angles = self._derive_pitch_angles()
        if self.yaw_angles == 'derived':
            if self.multiple_position_sensors:
                self.yaw_angles = self._derive_yaw_angles_multi()
            else:
                self.yaw_angles = self._derive_yaw_angles_single()
    
    def _calculate_platform_height(self):
        '''
        Read in height above ground measurements for each height sensor, adjust the heights to be relative
        to platform origin and average them.  The fixed height will also be read in which will be None
        if not specified by user or not valid.
        '''
        height_measurements_by_source = self.session_output.read_heights_above_ground()
        
        # Make sure all units are in meters.
        for source_name, height_measurements in height_measurements_by_source.iteritems():
            height_source = self.session_output.find_matching_height_source(source_name)
            standard_heights = self._standardize_heights(height_measurements, height_source) 
            height_measurements_by_source[source_name] = standard_heights
            
        # TODO reference heights from platform origin.
            
        num_height_sources = len(height_measurements_by_source)
                
        if num_height_sources > 1:
            self.log.warning('Multiple height sources detected but only 1 is supported right now.')
            self.heights = height_measurements_by_source.values()[0]
        elif num_height_sources == 1:
            self.heights = height_measurements_by_source.values()[0]
            
        # User can also specify a fixed height above ground if no sensor is available or to use as a backup.
        self.fixed_height = self.session_output.read_fixed_height_above_ground()
        try:
            self.fixed_height = float(self.fixed_height)
        except (ValueError, TypeError):
            self.fixed_height = None
            
        # TODO take into account sensor offset relative to GPS
        
    def _standardize_heights(self, distances, source):
        '''Return updated list of height distances for the specified source that are in meters.'''
        
        if contains_measurements(distances):
            sensor_info = self.session_output.find_matching_sensor_info(source)
            try:
                units = sensor_units(sensor_info, source['height_index'])
            except:
                self.log.warn('Units not listed for height source. Assuming meters.')
                units = 'meters'
            distances = standardize_to_meters(distances, units, 'height')
            
        return distances
    
    def _calculate_platform_state(self):
        '''
        Synchronize different parts of platform state (position, orientation, etc) to occur at
        the same time-stamps and return results as a list of ObjectStates.
        '''
        # Determine if Euler angles and height measurements are available to use.
        valid_roll_angles = contains_measurements(self.roll_angles)
        valid_pitch_angles = contains_measurements(self.pitch_angles)
        valid_yaw_angles = contains_measurements(self.yaw_angles)
        valid_height_measurements = contains_measurements(self.heights)
        valid_fixed_height = self.fixed_height is not None and self.fixed_height >= 0
        
        # Separate into time/value parts to get ready to interpolate below.
        if valid_roll_angles:
            roll_values = [a.angle for a in self.roll_angles]
            roll_times = [a.utc_time for a in self.roll_angles]
        if valid_pitch_angles:
            pitch_values = [a.angle for a in self.pitch_angles]
            pitch_times = [a.utc_time for a in self.pitch_angles]
        if valid_yaw_angles:
            yaw_values = [a.angle for a in self.yaw_angles]
            yaw_times = [a.utc_time for a in self.yaw_angles]
        if valid_height_measurements:
            height_values = [height.height for height in self.heights]
            height_times = [height.utc_time for height in self.heights]
        
        # Calculate state at same time as each position.
        platform_states = []
        
        for position in self.platform_positions:
            
            if valid_roll_angles:
                roll = closest_value(position.utc_time, roll_times, roll_values, max_x_diff=self.max_time_diff)
                if math.isnan(roll):
                    continue # don't use this position because it's missing roll information
            else:
                roll = float('NaN')
            
            if valid_pitch_angles:
                pitch = closest_value(position.utc_time, pitch_times, pitch_values, max_x_diff=self.max_time_diff)
                if math.isnan(pitch):
                    continue # don't use this position because it's missing pitch information
            else:
                pitch = float('NaN')
                
            if valid_yaw_angles:
                yaw = closest_value(position.utc_time, yaw_times, yaw_values, max_x_diff=self.max_time_diff)
                if math.isnan(yaw):
                    continue # don't use this position because it's missing yaw information
            else:
                yaw = float('NaN')

            if valid_height_measurements:
                height = interpolate_single(position.utc_time, height_times, height_values, max_x_diff=self.max_time_diff)
                if math.isnan(height) and not valid_fixed_height:
                    continue # don't use this position because it's missing height information and no fixed height to use as backup
            else:
                height = float('NaN')
                
            if math.isnan(height) and valid_fixed_height:
                height = self.fixed_height
                
            platform_state = ObjectState(position.utc_time, position.lat, position.long, position.alt,
                                         roll, pitch, yaw, height_above_ground=height)

            
            platform_states.append(platform_state)
            
        return platform_states
    
    def _calculate_sensor_states(self, sensors, platform_states):
        '''
        Return new list of sensors where each piece of data contains a 'state' key
        that stores the state of the sensor for that reading.
        If a state can't be calculated for a reading, then that reading is removed.
        If a sensor doesn't have any log data then that sensor is removed from the list.
        '''
        # Remove any sensors that don't have any log data since they essentially weren't used.
        sensors = [sensor for sensor in sensors if sensor['log_data'] is not None]
        
        # Go through and calculate position and orientations of all sensor measurements.
        # This will add a 'state' key for each data entry.
        for sensor in sensors:
    
            offsets_in_radians = [angle * math.pi/180.0 for angle in sensor['orientation_offsets']]
            
            # Account for fact that platform positions and sensor offsets may not have the same origin.
            position_offsets = np.asarray(sensor['position_offsets']) - np.asarray(self.platform_position_offset)
            
            # Save these 'adjusted' position offsets so we can upload them to the database.
            sensor['adjusted_position_offsets'] = list(position_offsets)
            
            self.geotagger.tag_all_readings(sensor['log_data'], position_offsets, offsets_in_radians, platform_states)
            
            # Keep track of how many measurements didn't match up with platform state based on time-stamps.
            num_unmatched_states = 0

            # Iterate over copy so we can delete data entries as we go.
            log_data_copy = sensor['log_data'][:]
            for data in log_data_copy:
                
                # Make sure sensor was assigned a position before trying to convert back to lat/lon.
                if math.isnan(data['state'].lat):
                    num_unmatched_states += 1
                    # Measurement is only valid if it has a position.  No point in keeping it otherwise.
                    # TODO could write unmatched entries out to another 'unmatched' log file. 
                    sensor['log_data'].remove(data)
                    continue
                
            if num_unmatched_states > 0:
                self.log.warn("Removed {} readings from {} since no matching state.".format(num_unmatched_states, sensor['sensor_id']))
                
        return sensors
            
    def _derive_roll_angles(self):
        '''
        Use synced position sources to determine platform roll. If there aren't multiple position sources then
        return None.  Otherwise angles returned as StampleAngles in degrees and +/- 180.
        '''
        self.log.warn("Deriving roll angles not currently supported.")
        #raise ValueError('Unsupported setting.  Roll angles cannot be derived right now.')
        return None

    def _derive_pitch_angles(self):
        '''
        Use synced position sources to determine platform pitch. If there aren't multiple position sources then
        return None.  Otherwise angles returned as StampleAngles in degrees and +/- 180.
        '''        
        self.log.warn("Deriving pitch angles not currently supported.")
        #raise ValueError('Unsupported setting.  Pitch angles cannot be derived right now.')
        return None
    
    def _derive_yaw_angles_multi(self):
        '''
        Use synced position sources to determine platform yaw. If there aren't multiple position sources then
        return None.  Otherwise angles returned as StampleAngles in degrees and +/- 180.
        '''
        # Determine offsets for each position sources along the 'right direction' (y-axis)
        # so that we can figure out which source is on the left side and which is on the right side.
        source_names = self.synced_platform_positions.keys()
        sensor_infos = [self.session_output.find_matching_sensor_info_by_name(name) for name in source_names]
        source_offsets = [info['position_offsets'] for info in sensor_infos]
        offsets_right = [offsets[1] for offsets in source_offsets]
        
        if abs(min(offsets_right) - max(offsets_right)) < 0.01:
            # We don't use offset spacing for determing yaw, but if we can't tell which is left/right
            # reliably then we yaw could be flipped 180 degrees.
            raise ValueError("Not enough spacing between position sources to derive yaw.")
        
        # Left most position source and right most position source.
        left_source_name = source_names[np.argmin(offsets_right)]
        right_source_name = source_names[np.argmax(offsets_right)]
        
        left_positions = self.synced_platform_positions[left_source_name]
        right_positions = self.synced_platform_positions[right_source_name]
        
        yaw_angles = []
                
        for left, right in zip(left_positions, right_positions):
            # First find relative bearing of vector from left position -> right position
            diff_lat = right.lat - left.lat
            diff_long = right.long - left.long
            rel_bearing = math.atan2(diff_long, diff_lat) * 180.0 / math.pi
            # Then find yaw of platform which is at 90 degrees to this relative bearing
            # and ensure it's within +/- 180 degrees.
            yaw = rel_bearing  - 90.0
            yaw = wrap_angle_degrees(yaw)
            
            # Both positions should be at same time so it doesn't matter which one we use.
            yaw_angles.append(StampedAngle(left.utc_time, yaw))
    
        return yaw_angles
    
    def _derive_yaw_angles_single(self, platform_positions):
        '''
        Use change in platform position to determine platform yaw.
        '''
        self.log.warn("Deriving yaw from single position source isn't supported yet.")
        #raise ValueError("Deriving yaw from single position source isn't supported yet.")
        return None
    
    def _sync_platform_positions(self, position_measurements_by_source):
        '''
        Return new dictionary of position measurements by source, but with each StampedPosition
        being at the same UTC time between all sources.  Right now uses first position source as
        reference times.
        '''
        synced_positions = defaultdict(list)
        
        source_names = position_measurements_by_source.keys()
        
        # Just use first source as reference source to match all the other position sources up to.
        ref_source_name = source_names[0]
        other_source_names = source_names[1:]
        
        synced_positions[ref_source_name] = position_measurements_by_source[ref_source_name]
        
        ref_source_times = [p.utc_time for p in position_measurements_by_source[ref_source_name]]
        
        for other_source_name in other_source_names:
            
            other_source_positions = position_measurements_by_source[other_source_name]
            other_source_times = [p.utc_time for p in other_source_positions]
            other_source_values = [(p.lat, p.long, p.alt) for p in other_source_positions]
            
            for ref_utc_time in ref_source_times:
                lat, long, alt = interpolate(ref_utc_time, other_source_times, other_source_values, max_x_diff=self.max_time_diff)
  
                synced_positions[other_source_name].append(StampedPosition(ref_utc_time, lat, long, alt))
            
        return synced_positions
    
    def _remove_unmatched_positions(self, synced_platform_positions):
        '''Return new dictionary that only includes positions which are are matched (i.e. not NaN) for all sources.'''
        
        filtered_positions = {}
        
        positions_by_time = zip(*synced_platform_positions.values())
        
        matched_indices = []
        for idx, positions in enumerate(positions_by_time):
            if float('NaN') not in [p.lat for p in positions]:
                matched_indices.append(idx)
        
        for source_name, source_positions in synced_platform_positions.iteritems():
            matched_positions = [source_positions[i] for i in matched_indices]
            filtered_positions[source_name] = matched_positions
        
        return filtered_positions
    
    def _average_platform_positions(self, synced_platform_positions):
        '''Return list of StampedPositions from averaging lat/long/alt from multiple positions sources'''
        
        averaged_positions = []

        for positions in zip(*synced_platform_positions.values()):
            
            avg_lat, avg_long, avg_alt = np.mean([p.position_tuple for p in positions], axis=0)
            
            # All positions should have the same time so it doesn't matter which we use.
            utc_time = positions[0].utc_time
            
            avg_position = StampedPosition(utc_time, avg_lat, avg_long, avg_alt)
            
            averaged_positions.append(avg_position)
        
        return averaged_positions
