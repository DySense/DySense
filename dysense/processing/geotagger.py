#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
import os
import csv
import argparse
import math

from dysense.core.utility import closest_value, find_less_than_or_equal, interpolate, wrap_angle_radians

class GeoReading(object):
    '''Sensor reading with position/orientation information.'''
    def __init__(self, time, data, position, orientation):
        self.time = time
        self.data = data
        self.position = position
        self.orientation = orientation
        
class GeoTagger(object):

    def __init__(self, max_time_diff, log):
        
        self.max_time_diff = max_time_diff
        self.log = log

    def tag_all_readings(self, readings, position_offsets, orientation_offsets, positions, roll_angles, pitch_angles, yaw_angles):
        '''Assumes everything is already sorted by time.'''
        # Split position measurements by axes for interpolation.
        x_values = [p.x for p in positions]
        y_values = [p.y for p in positions]
        z_values = [p.z for p in positions]
        positions_by_axes = [x_values, y_values, z_values]
        
        position_times = [p.utc_time for p in positions]
        
        # Separate angles into time/value parts.
        if roll_angles is not None:
            roll_values = [a.angle for a in roll_angles]
            roll_times = [a.utc_time for a in roll_angles]
        if pitch_angles is not None:
            pitch_values = [a.angle for a in pitch_angles]
            pitch_times = [a.utc_time for a in pitch_angles]
        if yaw_angles is not None:
            yaw_values = [a.angle for a in yaw_angles]
            yaw_times = [a.utc_time for a in yaw_angles]
        
        for reading in readings:
            reading_position = self.interpolate_position(reading['time'], position_times, positions_by_axes)
            
            if roll_angles is not None:
                reading_roll = self.closest_angle_by_time(reading['time'], roll_times, roll_values)
            else:
                reading_roll = float('nan')
            
            if pitch_angles is not None:
                reading_pitch = self.closest_angle_by_time(reading['time'], pitch_times, pitch_values)
            else:
                reading_pitch = float('nan')
            
            if yaw_angles is not None:
                reading_yaw = self.closest_angle_by_time(reading['time'], yaw_times, yaw_values)
            else:
                reading_yaw = float('nan') 
            
            self.tag_reading(reading, reading_position, reading_roll, reading_pitch, reading_yaw, position_offsets, orientation_offsets)
    
    def tag_reading(self, reading, position, roll, pitch, yaw, position_offsets, orientation_offsets):
        # Use heading to split body offsets into inertial x,y,z offsets
        x, y, z = position
        x_body, y_body, z_body = position_offsets
        
        # If no yaw
        # 1) and nonzero X,Y offsets make position nan
        # 2) can't use roll or pitch.
        
        # If no roll or pitch 
        # 1) if it wasn't provided by source then treat it as 0, but still store it as 'nan'
        # 2) if it couldn't be matched and non-zero XYZ offsets we should have it then invalidate position since position won't be right.
        
        if math.isnan(roll):
            roll = 0
            
        if math.isnan(pitch):
            pitch = 0
            
        if math.isnan(yaw):
            yaw = 0
        
        # TODO take into account roll and pitch for calculating offsets.  
        x_offset = x_body * math.cos(yaw) - y_body * math.sin(yaw)
        y_offset = x_body * math.sin(yaw) + y_body * math.cos(yaw)
        z_offset = z_body
        
        # Add on offsets to position.
        x += x_offset
        y += y_offset
        z += z_offset
        
        # TODO account for roll/pitch orientation offsets correctly.
        roll_offset, pitch_offset, yaw_offset = orientation_offsets
        yaw += yaw_offset
        
        if yaw_offset > 1.5 and yaw_offset < 1.7: # +90
            # TODO do this correctly Switch 
            # roll and pitch (ro = roll original)
            ro = roll
            po = pitch
            roll = po
            pitch = -ro 
        elif yaw_offset < -1.5 and yaw_offset > -1.7: # -90
            # TODO do this correctly
            # Switch roll and pitch (ro = roll original)
            ro = roll
            po = pitch
            roll = -po
            pitch = ro
            
        # Ensure angles are between +/- PI.
        roll = wrap_angle_radians(roll)
        pitch = wrap_angle_radians(pitch)
        yaw = wrap_angle_radians(yaw)
        
        reading['position'] = (x, y, z)
        reading['orientation'] = (roll, pitch, yaw)
    
    def closest_position_by_time(self, reading_time, position_times, position_values):
        ''''''
        return closest_value(reading_time, position_times, position_values, max_x_diff=self.max_time_diff)
    
    def closest_angle_by_time(self, reading_time, angle_times, angle_values):
        ''''''
        return closest_value(reading_time, angle_times, angle_values, max_x_diff=self.max_time_diff)
    
    def interpolate_position(self, reading_time, position_times, position_values_by_axes):
        ''''''
        time_index = find_less_than_or_equal(position_times, reading_time)  
        x = interpolate(reading_time, position_times, position_values_by_axes[0], i1=time_index, max_x_diff=self.max_time_diff)
        y = interpolate(reading_time, position_times, position_values_by_axes[1], i1=time_index, max_x_diff=self.max_time_diff)
        z = interpolate(reading_time, position_times, position_values_by_axes[2], i1=time_index, max_x_diff=self.max_time_diff)
    
        return (x, y, z)
    
    def interpolate_orientation(self, reading_time, orientation_times, orientations_by_axes):
        ''''''
        self.log.critical("Interpolation not currently supported for orientation. Exiting")
        sys.exit(1)
    
        orientation_index = find_less_than_or_equal(orientation_times, reading_time)
        angle1 = interpolate(reading_time, orientation_times, orientations_by_axes[0], i1=orientation_index, max_x_diff=self.max_time_diff)
        angle2 = interpolate(reading_time, orientation_times, orientations_by_axes[1], i1=orientation_index, max_x_diff=self.max_time_diff)
        angle3 = interpolate(reading_time, orientation_times, orientations_by_axes[2], i1=orientation_index, max_x_diff=self.max_time_diff)
        
        return (angle1, angle2, angle3)


