# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import numpy as np
from math import cos 

from dysense.processing.platform_state import platform_state_at_times
from dysense.processing.utility import ObjectState, effective_angle_rad, actual_angle_deg
from dysense.processing.utility import rpy_from_rot_matrix, rot_parent_to_child
from dysense.processing.log import log
        
class GeoTagger(object):
    '''Determine state of sensor readings.'''

    def __init__(self, max_time_diff):
        '''Constructor.'''
        
        self.max_time_diff = max_time_diff

    def tag_all_readings(self, readings, position_offsets, orientation_offsets, platform_states):
        '''
        Find sensor state at each reading by combining platform states with sensor offsets.
        This will add a 'state' key to each reading in 'readings'.  
        If the state couldn't be determined then the position (e.g. latitude) will be set to NaN. 
        Assumes everything is already sorted by time.
        '''
        reading_times = [reading['time'] for reading in readings]
       
        platform_state_at_readings = platform_state_at_times(platform_states, reading_times, self.max_time_diff)
       
        # Determine rotation matrix to rotate vector from platform frame to sensor frame.
        # Do this once since it doesn't change between readings.
        platform_to_sensor_rot_matrix = rot_parent_to_child(*orientation_offsets)
        
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
        platform_roll_rad = effective_angle_rad(platform.roll) 
        platform_pitch_rad = effective_angle_rad(platform.pitch)
        platform_yaw_rad = effective_angle_rad(platform.yaw)
        
        # Determine rotation matrix to convert between world and platform frames.
        world_to_platform_rot_matrix = rot_parent_to_child(platform_roll_rad, platform_pitch_rad, platform_yaw_rad)
        
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
        sensor_roll, sensor_pitch, sensor_yaw = actual_angle_deg(sensor_orientation_rad, platform.orientation)
        
        sensor_state = ObjectState(utc_time, sensor_lat, sensor_long, sensor_alt,
                                    sensor_roll, sensor_pitch, sensor_yaw, sensor_height)
        
        return sensor_state
