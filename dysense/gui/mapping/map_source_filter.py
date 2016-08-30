# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import sys
import time
from collections import namedtuple

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from dysense.gui.mapping.utility import SourcePositionManager, SourcePosition
from dysense.core.utility import average

class MapSourceFilter(QtGui.QWidget):
    
    def __init__(self, min_update_period):
        '''Constructor'''
        QtGui.QWidget.__init__(self)
        
        # Associate (controller_id, sensor_id) with a source manager.
        self.id_to_sources = {}
        
        # The last system time that a point was returned by filter
        self.last_utc_time_update = 0
        
        # Minimum time to wait before adding new point.
        self.min_update_period = min_update_period
        
    def reset(self):
        
        self.id_to_sources = {}
        self.last_utc_time_update = 0
        
    def filter(self, position, controller_id, sensor_id, expected_sources):
        
        source_id = (controller_id, sensor_id)

        try:
            source = self.id_to_sources[source_id]
        except KeyError:
            # New source
            source = SourcePositionManager()
            self.id_to_sources[source_id] = source
        
        source.add_position(position)
        
        time_since_last_point = position.utc_time - self.last_utc_time_update
        
        if time_since_last_point < self.min_update_period:
            return None # not enough time has elapsed.
        
        if len(expected_sources) > 1:
            position = self._try_merge_positions(expected_sources)
        elif len(expected_sources) == 0:
            return None
        
        if position is not None:
            self.last_utc_time_update = position.utc_time
        
        return position
    
    def _try_merge_positions(self, expected_sources):
        
        if not self._receiving_all_expected_sources(expected_sources):
            return None

        for source in self.id_to_sources.itervalues():
            
            new_enough_data = source.latest_utc_time > self.last_utc_time_update
            
            if not new_enough_data or not source.has_multiple_positions:
                return None
            
        common_utc_time = min([source.latest_utc_time for source in self.id_to_sources.itervalues()])
            
        positions_at_common_times = [source.position_at(common_utc_time) for source in self.id_to_sources.itervalues()]

        average_lat = average([position[0] for position in positions_at_common_times])
        average_lon = average([position[1] for position in positions_at_common_times])
        average_alt = average([position[2] for position in positions_at_common_times])
        
        print common_utc_time
        
        if math.isnan(average_lat):
            return None

        merged_position = SourcePosition(common_utc_time, average_lat, average_lon, average_alt)
        
        for source in self.id_to_sources.itervalues():
            source.filter_old_positions(common_utc_time)

        return merged_position
    
    def _receiving_all_expected_sources(self, expected_sources):
        
        for expected_source in expected_sources:
            expected_id = (expected_source['controller_id'], expected_source['sensor_id'])
            if expected_id not in self.id_to_sources:
                return False # missing an expected source
        
        return True # receiving all expected sources
        