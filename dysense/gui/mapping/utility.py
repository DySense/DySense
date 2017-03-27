# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import sys
import time
from collections import namedtuple

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from dysense.core.utility import interp_list_from_set, find_less_than_or_equal

class SourcePosition(object):
    '''Time stamped position measurement.'''

    def __init__(self, utc_time, lat, long, alt):
        self.utc_time = utc_time
        self.lat = lat
        self.long = long
        self.alt = alt

    @property
    def coordinates(self):
        return (self.lat, self.long, self.alt)

class MapPosition(object):
    '''Time stamped position measurement.'''

    def __init__(self, utc_time, easting, northing, alt, tags=None):
        self.utc_time = utc_time
        self.easting = easting
        self.northing = northing
        self.alt = alt

class SourcePositionManager():

    def __init__(self):

        self.reference_position = None
        self._position_times = []
        self._position_coordinates = []
        self._last_received_sys_time = 0

    @property
    def latest_utc_time(self):
        try:
            return self._position_times[-1]
        except IndexError:
            return -1

    @property
    def has_multiple_positions(self):
        return len(self._position_times) > 1

    def timed_out(self):
        return (self._last_received_sys_time + 5) < time.time()

    def add_position(self, source_position):

        if len(self._position_times) > 1:
            time_since_last_position = self._position_times[-1] - source_position.utc_time
            if time_since_last_position > 10:
                self._position_times = []
                self._position_coordinates = []

        self._position_times.append(source_position.utc_time)
        self._position_coordinates.append(source_position.coordinates)

        if len(self._position_times) > 100:
            self.filter_old_positions(source_position.utc_time)

    def filter_old_positions(self, utc_time):

        closest_time_idx = find_less_than_or_equal(self._position_times, utc_time)

        try:
            self._position_times = self._position_times[closest_time_idx:]
            self._position_coordinates = self._position_coordinates[closest_time_idx:]
        except IndexError:
            return # all saved times are after specified utc_time so keep them all

    def position_at(self, utc_time):

        return interp_list_from_set(utc_time, self._position_times, self._position_coordinates, max_x_diff=2)
