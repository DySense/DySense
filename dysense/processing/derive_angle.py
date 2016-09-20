# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math

import numpy as np

from dysense.processing.utility import wrap_angle_degrees, StampedAngle

def derive_roll_angles(synced_position_sources):
    '''
    Use synced position sources to determine platform roll. If there aren't multiple position sources then
    return None.  Otherwise angles returned as StampleAngles in degrees and +/- 180.
    '''
    self.log.warn("Deriving roll angles not currently supported.")
    #raise ValueError('Unsupported setting.  Roll angles cannot be derived right now.')
    return None

def derive_pitch_angles(synced_position_sources):
    '''
    Use synced position sources to determine platform pitch. If there aren't multiple position sources then
    return None.  Otherwise angles returned as StampleAngles in degrees and +/- 180.
    '''        
    self.log.warn("Deriving pitch angles not currently supported.")
    #raise ValueError('Unsupported setting.  Pitch angles cannot be derived right now.')
    return None

def derive_yaw_angles_multi(synced_platform_positions, sensor_infos):
    '''
    Use synced position sources to determine platform yaw. If there aren't multiple position sources then
    return None.  Otherwise angles returned as StampleAngles in degrees and +/- 180.
    '''
    # Determine offsets for each position sources along the 'right direction' (y-axis)
    # so that we can figure out which source is on the left side and which is on the right side.
    source_names = synced_platform_positions.keys()
    source_offsets = [info['position_offsets'] for info in sensor_infos]
    offsets_right = [offsets[1] for offsets in source_offsets]
    
    if abs(min(offsets_right) - max(offsets_right)) < 0.01:
        # We don't use offset spacing for determing yaw, but if we can't tell which is left/right
        # reliably then we yaw could be flipped 180 degrees.
        raise ValueError("Not enough spacing between position sources to derive yaw.")
    
    # Left most position source and right most position source.
    left_source_name = source_names[np.argmin(offsets_right)]
    right_source_name = source_names[np.argmax(offsets_right)]
    
    left_positions = synced_platform_positions[left_source_name]
    right_positions = synced_platform_positions[right_source_name]
    
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

def derive_yaw_angles_single(platform_positions):
    '''
    Use change in platform position to determine platform yaw.
    '''
    self.log.warn("Deriving yaw from single position source isn't supported yet.")
    #raise ValueError("Deriving yaw from single position source isn't supported yet.")
    return None