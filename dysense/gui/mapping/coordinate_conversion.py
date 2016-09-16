# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import sys

from dysense.gui.mapping.utility import MapPosition

class CoordinateConverter(object):
    '''Convert lat/long -> easting/northing -> pixel coordinates.'''
    
    def __init__(self, map_view):
        '''Constructor'''
        
        self.map_view = map_view

        # Convert lat/long to meters. Set once receive first latitude.
        self.meters_per_deg_lat = float('NaN')
        self.meters_per_deg_long = float('NaN')
        
        # Set to true when need to use the next latitude to calculate a new scale between degrees and meters.
        self._need_to_calculate_deg_scale = True
        
        # Convert meters to pixels
        self.pixels_per_meter_x = 0
        self.pixels_per_meter_y = 0
        
        # Set to true if conversion between meters and pixels is same on both axes
        self.fixed_ratio = False
        
        self.reset_bounds()

    def reset_bounds(self):
        '''Set bounds to extremes so they will be overwritten by next valid position'''
        self.min_northing = sys.float_info.max
        self.max_northing = -sys.float_info.max
        self.min_easting = sys.float_info.max
        self.max_easting = -sys.float_info.max
            
    def convert_to_map_position(self, position):
        '''Convert specified SourcePosition to a MapPosition and return the result.'''
        if self._need_to_calculate_deg_scale:
            ref_lat = position.lat * math.pi / 180
            self.meters_per_deg_lat = (111132.92-559.82*math.cos(2*ref_lat)+1.175*math.cos(4*ref_lat))
            self.meters_per_deg_long = (111412.84*math.cos(ref_lat) - 93.5*math.cos(3*ref_lat))
            self._need_to_calculate_deg_scale = False
            
        # Convert to meters since we need to plot in 2D plane and meters are easy for user to understand.
        north_meters = self.meters_per_deg_lat * position.lat
        east_meters = self.meters_per_deg_long * position.long
        
        return MapPosition(position.utc_time, east_meters, north_meters, position.alt)
        
    def need_to_calculate_pixel_scale(self, position):
        '''
        Return true if specified MapPosition is outside the current max/min.
        For efficiency reasons the bounds are updated in this method.
        '''
        need_to_rescale = False

        if position.northing < self.min_northing:
            self.min_northing = position.northing
            need_to_rescale = True
        if position.northing > self.max_northing:
            self.max_northing = position.northing
            need_to_rescale = True
        if position.easting < self.min_easting:
            self.min_easting = position.easting
            need_to_rescale = True
        if position.easting > self.max_easting:
            self.max_easting = position.easting
            need_to_rescale = True

        return need_to_rescale
        
    def calculate_new_pixel_scale(self):
        '''Calculate new scale based on size of map_view and current bounds.'''
        northing_span = self.max_northing - self.min_northing
        easting_span = self.max_easting - self.min_easting
        
        try:
            self.pixels_per_meter_y = self.map_view.drawable_height / northing_span
        except ZeroDivisionError:
            self.pixels_per_meter_y = float('NaN')
            
        try:
            self.pixels_per_meter_x = self.map_view.drawable_width / easting_span
        except ZeroDivisionError:
            self.pixels_per_meter_x = float('NaN')
            
        if self.fixed_ratio and not math.isnan(self.pixels_per_meter_x) and not math.isnan(self.pixels_per_meter_y):
            min_ratio = min([self.pixels_per_meter_x, self.pixels_per_meter_y])
            self.pixels_per_meter_x = min_ratio
            self.pixels_per_meter_y = min_ratio
            
    def convert_to_pixel_position(self, position):
        '''Convert MapPosition to x, y coordinates for map view.'''
        x_pix = (position.easting - self.min_easting) * self.pixels_per_meter_x
        y_pix = (position.northing - self.min_northing) * self.pixels_per_meter_y
        
        # Reverse y axis since origin is in top left.
        y_pix = self.map_view.drawable_height - y_pix
            
        return x_pix, y_pix
