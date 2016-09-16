# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import numpy as np
from math import sin, cos, atan2, asin

from dysense.core.utility import closest_value, interpolate, interpolate_single
from dysense.processing.utility import ObjectState
        
class GeoTagger(object):
    '''Determine state of sensor readings.'''

    def __init__(self, max_time_diff, log):
        '''Constructor.'''
        
        self.max_time_diff = max_time_diff
        self.log = log

    def tag_all_readings(self, readings, position_offsets, orientation_offsets, platform_states):
        '''
        Find sensor state at each reading by combining platform states with sensor offsets.
        This will add a 'state' key to each reading in 'readings'.  
        If the state couldn't be determined then the position (e.g. latitude) will be set to NaN. 
        Assumes everything is already sorted by time.
        '''
        reading_times = [reading['time'] for reading in readings]
       
        platform_state_at_readings = self._platform_state_at_times(platform_states, reading_times)
       
        # Determine rotation matrix to rotate vector from platform frame to sensor frame.
        # Do this once since it doesn't change between readings.
        platform_to_sensor_rot_matrix = rot_parent_to_body(*orientation_offsets)
        
        for reading, platform_state_at_reading in zip(readings, platform_state_at_readings):
 
            sensor_state = self.caculate_sensor_state(reading['time'], position_offsets, platform_to_sensor_rot_matrix, platform_state_at_reading)
    
            reading['state'] = sensor_state
    
    def caculate_sensor_state(self, utc_time, position_offsets, platform_to_sensor_rot_matrix, platform):
        '''
        Return ObjectState associated with sensor at the specified UTC time.
        
        3 frames - sensor, platform, world 
        
          sensor frame: fixed to body of sensor, if sensor is pointed at ground can consider a 'forward-right-down' (FRD) system.
                        where positive z-axis in direction of reading, x-axis out of the top of the sensor.
        
          platform frame: fixed to body of platform, also a 'forward-right-down' (FRD) system.  Origin is where the lat/long/alt
                          of the specified platform state is measured at.
                          
          world frame: specified as lat/long/alt in WGS-84 ellipsoid.
        
        'position_offsets' should be a numpy array and are measured in meters in the platform_frame. 
        'platform' is the platform state at the specified utc_time
        '''

        # TODO account for no yaw
        
        # If an angle wasn't measured by the platform then want to treat it as 0 for these calculations since that's our best guess.
        # This will also convert the angles to radians.
        platform_roll_rad = self._effective_angle_rad(platform.roll) 
        platform_pitch_rad = self._effective_angle_rad(platform.pitch)
        platform_yaw_rad = self._effective_angle_rad(platform.yaw)
        
        # Determine rotation matrix to convert between world and platform frames.
        world_to_platform_rot_matrix = rot_parent_to_body(platform_roll_rad, platform_pitch_rad, platform_yaw_rad)
        
        # Combine rotation so we can extract Euler angles from rotation matrix to get sensor orientation relative to world frame.
        world_to_sensor_rot_matrix = np.dot(world_to_platform_rot_matrix, platform_to_sensor_rot_matrix)
        sensor_orientation_rad = rpy_from_rot_matrix(world_to_sensor_rot_matrix)
        
        # Rotate sensor offsets to be in world (NED) frame.
        platform_to_world_rot_matrix = world_to_platform_rot_matrix.transpose()
        sensor_north_offset, sensor_east_offset, sensor_down_offset_world = np.dot(platform_to_world_rot_matrix, position_offsets)
    
        # Convert platform lat/long to NED (in meters) so we can add in sensor offsets which are also in meters.
        # This uses a linear approximation which changes based on the reference latitude.  
        # See: https://en.wikipedia.org/wiki/Geographic_coordinate_system#Expressing_latitude_and_longitude_as_linear_units
        ref_lat = platform.lat * math.pi / 180.0
        meters_per_deg_lat = 111132.92 - 559.82*cos(2.0*ref_lat) + 1.175*cos(4.0*ref_lat) - 0.0023*cos(6.0*ref_lat)
        meters_per_deg_long = 111412.84*cos(ref_lat) - 93.5*cos(3.0*ref_lat) + 0.118*cos(5.0*ref_lat)
        
        # These northing/easting are not geodetically meaningful (in an accuracy sense),
        # since the linear approximation only applies to this degree of latitude, not all degrees..
        # but that's ok since we're just dealing with small, temporary position offsets.
        platform_northing = platform.lat * meters_per_deg_lat
        platform_easting = platform.long * meters_per_deg_long
        platform_down = -platform.alt
        
        # Find sensor position in NED and then convert back to LLA.
        sensor_northing = platform_northing + sensor_north_offset
        sensor_easting = platform_easting + sensor_east_offset
        sensor_down_world = platform_down + sensor_down_offset_world

        sensor_lat = sensor_northing / meters_per_deg_lat
        sensor_long = sensor_easting / meters_per_deg_long
        sensor_alt = -sensor_down_world
        sensor_height = platform.height_above_ground - sensor_down_offset_world
        
        # Convert angles back to NaN if platform didn't actually record those angles (storing it as 0 would be misleading)
        # and also convert back to degrees since that's how angles are stored.
        sensor_roll, sensor_pitch, sensor_yaw = self._actual_angle_deg(sensor_orientation_rad, platform.orientation)
        
        sensor_state = ObjectState(utc_time, sensor_lat, sensor_long, sensor_alt,
                                    sensor_roll, sensor_pitch, sensor_yaw, sensor_height)
        
        return sensor_state
    
    def _platform_state_at_times(self, platform_states, utc_times):
        '''Return list of platform states at the specified utc_times.'''
    
        # TODO - once interpolate orientation using quaternians could interpolate everything at once in one big list
        platform_times = [state.utc_time for state in platform_states]
        platform_positions = [state.position for state in platform_states]
        platform_roll_angles = [state.roll for state in platform_states]
        platform_pitch_angles = [state.pitch for state in platform_states]
        platform_yaw_angles = [state.yaw for state in platform_states]
        platform_heights = [state.height_above_ground for state in platform_states]  
        
        platform_states_at_times = []

        for utc_time in utc_times:
            lat, long, alt = interpolate(utc_time, platform_times, platform_positions)
            roll = closest_value(utc_time, platform_times, platform_roll_angles, max_x_diff=self.max_time_diff)
            pitch = closest_value(utc_time, platform_times, platform_pitch_angles, max_x_diff=self.max_time_diff)
            yaw = closest_value(utc_time, platform_times, platform_yaw_angles, max_x_diff=self.max_time_diff)
            height = interpolate_single(utc_time, platform_times, platform_heights)
    
            new_state = ObjectState(utc_time, lat, long, alt, roll, pitch, yaw, height)
            
            platform_states_at_times.append(new_state)
    
        return platform_states_at_times
    
    def _effective_angle_rad(self, angle_deg):
        '''Return angle converted to radians or 0 if angle is Nan'''
        
        if math.isnan(angle_deg):
            return 0.0
        else:
            return angle_deg * math.pi / 180.0
    
    def _actual_angle_deg(self, sensor_angles_rad, platform_angles):
        '''Return angles where each angle is converted to degrees or NaN if the corresponding platform angle is NaN'''
        
        actual_sensor_angles = []
        for sensor_angle, platform_angle in zip(sensor_angles_rad, platform_angles):
            if math.isnan(platform_angle):
                actual_sensor_angles.append(float('NaN'))
            else:
                actual_sensor_angles.append(sensor_angle * 180.0 / math.pi)
   
        return actual_sensor_angles
  
def rot_parent_to_body(roll, pitch, yaw):
    '''
    Return 3x3 rotation matrix that will transform a vector in the parent frame to the body frame.
    Specified angles should be in radians and represent a right-handed positive rotation.
    This is done in the sequence z->y'->x'' which is an active, intrinsic rotation commonly called Euler ZYX
    This matrix is equivalent to an x->y->z active, extrinsic rotation commonly called Roll-Pitch-Yaw matrix.
    To go the opposite direction (body -> world) then take the transpose of this matrix which is equivalent to the inverse.
    ''' 
    rot_zy = np.dot(rot_z(yaw), rot_y(pitch))  
    return np.dot(rot_zy, rot_x(roll))
  
def rot_x(a):
    '''Return 3x3 positive rotation matrix about X axis by an angle 'a' specified in radians.'''
    
    return np.array([[1,   0,       0   ],
                     [0, cos(a), -sin(a)],
                     [0, sin(a),  cos(a)]])
    
def rot_y(a):
    '''Return 3x3 positive rotation matrix about Y axis by an angle 'a' specified in radians.'''
    
    return np.array([[ cos(a), 0,  sin(a)],
                     [   0,    1,    0   ],
                     [-sin(a), 0,  cos(a)]])
    
def rot_z(a):
    '''Return 3x3 positive rotation matrix about Z axis by an angle 'a' specified in radians.'''
    
    return np.array([[cos(a), -sin(a), 0],
                     [sin(a),  cos(a), 0],
                     [  0,       0,    1]])

def rpy_from_rot_matrix(r):
    '''
    Return [roll, pitch, yaw] angles in radians associated with active, extrinsic Roll-Pitch-Yaw matrix 'r'.
    Roll and yaw will be between +/- PI and pitch will be between +/- PI/2
    '''
    roll = atan2(r[2,1], r[2,2])
    pitch = -asin(r[2,0])
    yaw = atan2(r[1,0], r[0, 0])
    
    return [roll, pitch, yaw]
