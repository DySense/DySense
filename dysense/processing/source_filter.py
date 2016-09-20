# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
import math

import numpy as np

from dysense.processing.utility import StampedPosition, StampedHeight
from dysense.core.utility import interpolate, interpolate_single

def sync_platform_positions(position_measurements_by_source, max_time_diff):
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
            lat, long, alt = interpolate(ref_utc_time, other_source_times, other_source_values, max_x_diff=max_time_diff)
    
            synced_positions[other_source_name].append(StampedPosition(ref_utc_time, lat, long, alt))
        
    return synced_positions
    
def remove_unmatched_positions(synced_platform_positions):
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

def average_platform_positions(synced_platform_positions):
    '''Return list of StampedPositions from averaging lat/long/alt from multiple positions sources'''
    
    averaged_positions = []

    for positions in zip(*synced_platform_positions.values()):
        
        avg_lat, avg_long, avg_alt = np.mean([p.position_tuple for p in positions], axis=0)
        
        # All positions should have the same time so it doesn't matter which we use.
        utc_time = positions[0].utc_time
        
        avg_position = StampedPosition(utc_time, avg_lat, avg_long, avg_alt)
        
        averaged_positions.append(avg_position)
    
    return averaged_positions

def sync_platform_heights(height_measurements_by_source, max_time_diff):
    '''
    Return new dictionary of height measurements by source, but with each StampedHeight
    being at the same UTC time between all sources.  Right now uses first height source as
    reference times.
    '''
    synced_heights = defaultdict(list)
    
    source_names = height_measurements_by_source.keys()
    
    # Just use first source as reference source to match all the other height sources up to.
    ref_source_name = source_names[0]
    other_source_names = source_names[1:]
    
    synced_heights[ref_source_name] = height_measurements_by_source[ref_source_name]
    
    ref_source_times = [h.utc_time for h in height_measurements_by_source[ref_source_name]]
    
    for other_source_name in other_source_names:
        
        other_source_heights = height_measurements_by_source[other_source_name]
        other_source_times = [h.utc_time for h in other_source_heights]
        other_source_values = [h.height for h in other_source_heights]
        
        for ref_utc_time in ref_source_times:
            height_at_ref_time = interpolate_single(ref_utc_time, other_source_times, other_source_values, max_x_diff=max_time_diff)

            synced_heights[other_source_name].append(StampedHeight(ref_utc_time, height_at_ref_time))
        
    return synced_heights

def average_multiple_height_sources(synced_platform_heights):
    '''
    Return list of StampedHeight's from averaging height from multiple sources.
    If any averaging results in NaN then that result is excluded.
    '''
    averaged_heights = []

    for heights in zip(*synced_platform_heights.values()):
        
        avg_height = np.mean([h.height for h in heights])
    
        if math.isnan(avg_height):
            continue # sources didn't all have height at this time.
        
        # All heights should have the same time so it doesn't matter which we use.
        avg_stamped_height = StampedHeight(heights[0].utc_time, avg_height)
        
        averaged_heights.append(avg_stamped_height)
    
    return averaged_heights
