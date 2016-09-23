# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import numpy as np

from dysense.core.utility import interp_list_from_set, interp_single_from_set, interp_angle_deg_from_set
from dysense.processing.utility import ObjectState

def platform_state_at_times(platform_states, utc_times, max_time_diff):
    '''Return list of platform states at the specified utc_times.'''

    platform_times = [state.utc_time for state in platform_states]
    platform_positions = [state.position for state in platform_states]
    platform_roll_angles = [state.roll for state in platform_states]
    platform_pitch_angles = [state.pitch for state in platform_states]
    platform_yaw_angles = [state.yaw for state in platform_states]
    platform_heights = [state.height_above_ground for state in platform_states]  
    
    platform_states_at_times = []

    for utc_time in utc_times:
        # Interpolate all values so they occur at 'utc_time'
        lat, long, alt = interp_list_from_set(utc_time, platform_times, platform_positions, max_x_diff=max_time_diff)
        roll = interp_angle_deg_from_set(utc_time, platform_times, platform_roll_angles, max_x_diff=max_time_diff)
        pitch = interp_angle_deg_from_set(utc_time, platform_times, platform_pitch_angles, max_x_diff=max_time_diff)
        yaw = interp_angle_deg_from_set(utc_time, platform_times, platform_yaw_angles, max_x_diff=max_time_diff)
        height = interp_single_from_set(utc_time, platform_times, platform_heights, max_x_diff=max_time_diff)

        new_state = ObjectState(utc_time, lat, long, alt, roll, pitch, yaw, height)
        
        platform_states_at_times.append(new_state)

    return platform_states_at_times

def filter_down_platform_state(session, max_rate):
    '''
    Updates 'platform_state' key in session to not store any entries faster than specified rate.
    If rate is less than or equal to zero then won't limit entries at all.
    '''
    states = session['platform_states']
    
    if max_rate <= 0.0 or len(states) == 0:
        return # Don't limit platform state at all.
    
    min_time_between_states = 1.0 / max_rate
    
    # Add in a little wiggle room since time won't be exact. 
    min_time_between_states *= 0.9
    
    filtered_states = []
    last_state_time = states[0].utc_time
    for state in states[1:]:
        if state.utc_time - last_state_time >= min_time_between_states:
            filtered_states.append(state)
            last_state_time = state.utc_time

    session['platform_states'] = filtered_states
    
def sensor_distance_to_platform_frame(distance, sensor_to_platform_rot_matrix, position_offsets):
    '''
    Return new distance that is described in platform frame rather than sensor frame.
    The specified rotation matrix should rotate a vector in the sensor frame to the platform frame. 
    '''
    # Sensor frame has positive 'z' in direction of reading.
    distance_vector = np.array([0, 0, distance])
    
    # Describe vector in terms of FRD platform coordinate system.
    forward, right, down = np.dot(sensor_to_platform_rot_matrix, distance_vector)

    # Account for additional 'down' offset due to sensor not being mounted at same height as platform.
    distance_in_platform_frame = down + position_offsets[2]

    return distance_in_platform_frame