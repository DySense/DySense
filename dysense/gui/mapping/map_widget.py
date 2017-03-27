# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import islice
import time
import sys
import math

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from dysense.gui.mapping.map_view import MapView
from dysense.gui.mapping.map_source_filter import MapSourceFilter
from dysense.gui.mapping.coordinate_conversion import CoordinateConverter
from dysense.gui.mapping.utility import SourcePosition
from dysense.core.utility import make_unicode

class MapWidget(QtGui.QWidget):
    '''Draw lat/long positions from one or more position sources onto a 2D map.'''

    def __init__(self, presenter):
        '''Constructor'''
        QtGui.QWidget.__init__(self)

        self.presenter = presenter

        # Default and current value for minimum amount of time to wait before drawing map updates.
        self.default_min_update_distance = 1
        self.min_update_distance = self.default_min_update_distance

        # Actual widget where points are drawn.
        self.map_view = MapView(self)

        # Use to combine multiple sources into one position.
        self.source_filter = MapSourceFilter()

        # Use to move between different coordinate frames.
        self.converter = CoordinateConverter(self.map_view)

        # List of saved MapPositions. These are converted to pixel coordinates and drawn on the map.
        self.positions = []

        # Map positions that have been filtered, but not yet processed.
        self._cached_positions = []

        # Most recent position, regardless of whether or not it was saved in self.positions
        self.most_recent_position = None

        # Maximum amount of positions to remember before thinning some of them out.
        self.max_num_positions = 50

        # Flags to keep track of when to redraw all points.
        self._waiting_to_redraw = False
        self._time_to_redraw = False

        # Amount of time that has elapsed since last time map was redrawn.
        self._last_redraw_time = 0

        # Set to true when widget is being shown on screen.
        self._showing = False

        # Setup interface after map has been created.
        self._setup_ui()

        # Colors of different points.
        self.normal_point_color = Qt.green
        self.start_point_color = Qt.blue
        self.current_position_color = Qt.red

        # Connect signals to slots
        self.clear_map_button.clicked.connect(self._clear_map_button_clicked)
        self.update_rate_line_edit.textChanged.connect(self._update_rate_changed)
        self.fix_aspect_checkbox.toggled.connect(self._fix_aspect_toggled)

    def _distance_from_last_saved_position(self, new_position):
        try:
            last_saved_position = self.positions[-1]
        except IndexError:
            # No reference position so return high value so will definitely get saved.
            return sys.float_info.max

        diffx = last_saved_position.easting - new_position.easting
        diffy = last_saved_position.northing - new_position.northing
        return math.sqrt(diffx*diffx + diffy*diffy)

    @property
    def _time_since_last_redraw(self):
        return time.time() - self._last_redraw_time

    @property
    def _min_time_between_redraws(self):
        return 0 # TODO could base on # of positions

    def _time_since_most_recent_position(self, new_position):
        if self.most_recent_position is None:
            return new_position.utc_time
        return new_position.utc_time - self.most_recent_position.utc_time

    def showEvent(self, *args, **kwargs):
        QtGui.QWidget.showEvent(self, *args, **kwargs)

        self._showing = True
        for position in self._cached_positions:
            self._process_map_position(position)
        self._cached_positions = []

    def hideEvent(self, *args, **kwargs):
        QtGui.QWidget.hideEvent(self, *args, **kwargs)

        self._showing = False

    def update_for_new_position(self, controller_id, sensor_id, utc_time, sys_time, data, expected_sources):
        '''
        Try to plot new data (lat, long, alt) associated with specified position source.

        Return true if position is plotted on map. Position may be ignored depending on when last point was plotted
         or if other sources haven't reported data.

        Expected sources should be a list of all current position sources for the controller.
        '''
        try:
            lat, long, alt = data[:3]
        except ValueError:
            return False # not enough data provided

        new_position = SourcePosition(utc_time, lat, long, alt)

        filtered_position = self.source_filter.filter(new_position, controller_id, sensor_id, expected_sources)

        if filtered_position is None:
            return False # not enough data to merge from sources yet

        if self._time_since_most_recent_position(filtered_position) < 0.5:
            return False # limit how quickly we process

        # Convert lat/lon to cartesian frame.
        map_position = self.converter.convert_to_map_position(filtered_position)

        # Save reference so we can still show most recent position if we need to redraw all positions
        self.most_recent_position = map_position

        if self._showing:
            self._process_map_position(map_position)
        else:
            self._cached_positions.append(map_position)

    def _process_map_position(self, map_position):

        # Determine if should keep the point on the map.
        save_position = self._distance_from_last_saved_position(map_position) > self.min_update_distance

        if save_position:
            self.positions.append(map_position)

        need_to_rescale_map = self.converter.need_to_calculate_pixel_scale(map_position)

        # Make sure enough time has elapsed to avoid redrawing a ton of points too often.
        if need_to_rescale_map or self._waiting_to_redraw:
            if self._time_since_last_redraw < self._min_time_between_redraws:
                self._waiting_to_redraw = True
            else:
                self._time_to_redraw = True

        if self._time_to_redraw:
            self._calculate_new_pixel_scale()
            self._redraw_all_positions()
            self._time_to_redraw = False
            self._waiting_to_redraw = False
        else:
            self._draw_new_position(map_position, save_position)

        return True # position drawn successfully

    def clear_map(self):
        '''Delete all saved positions and everything drawn on map.'''
        self.positions = []
        self.converter.reset_bounds()
        self.source_filter.reset()
        self.map_view.reset_map()

    def _calculate_new_pixel_scale(self):

        if not self._showing:
            return # Don't

        self.converter.calculate_new_pixel_scale()

        self.map_view.update_pixels_per_meter(self.converter.pixels_per_meter_x)

    def _draw_new_position(self, position, save_position):
        '''Convert MapPosition to pixels and add to map.'''

        if len(self.positions) == 0:
            self._draw_start_position(position)
        elif save_position:
            self._draw_normal_position(position)

        # Always draw a temporary point showing the current position.
        self._draw_current_position(position)

    def _redraw_all_positions(self):
        '''Clear map and re-draw all saved positions.'''
        self.map_view.reset_map()

        if len(self.positions) == 0:
            return

        self._draw_start_position(self.positions[0])

        for position in islice(self.positions, 1, None):
            self._draw_normal_position(position)

        if self.most_recent_position is not None:
            self._draw_current_position(self.most_recent_position)

        self._last_redraw_time = time.time()

    def _draw_start_position(self, position):

        self._draw_map_position(position, temporary=False, color=self.start_point_color, radius=10, importance=1)

    def _draw_current_position(self, position):

        self._draw_map_position(position, temporary=True, color=self.current_position_color, radius=10, importance=2)

    def _draw_normal_position(self, position):

        self._draw_map_position(position, temporary=False, color=self.normal_point_color, radius=7)

    def _draw_map_position(self, position, temporary, color=Qt.black, radius=7, importance=0):

        x, y = self.converter.convert_to_pixel_position(position)
        self.map_view.draw_point(x, y, temporary, color, radius, importance)

    def _thin_positions(self):
        '''Remove every other position.'''
        self.positions = self.positions[0::2]

    def resizeEvent(self, *args, **kwargs):
        '''Calculate new scale and redraw everything. Called when widget changes size.'''
        self._calculate_new_pixel_scale()
        self.map_view.update_after_resize()
        self._redraw_all_positions()

    def _clear_map_button_clicked(self):

        question = "Are you sure you want to clear the map?"
        if not self.presenter.view.confirm_question(question):
            return

        self.clear_map()

    def _update_rate_changed(self):

        try:
            self.min_update_distance = float(self.update_rate_line_edit.text())
        except (ZeroDivisionError, ValueError):
            pass

    def _fix_aspect_toggled(self, is_checked):

        self.converter.fixed_ratio = is_checked
        self._calculate_new_pixel_scale()
        self._redraw_all_positions()

    def _setup_ui(self):

        self.widget_font = QFont('mapping_font', pointSize=12)

        self.clear_map_button = QtGui.QPushButton('Clear Map')
        self.clear_map_button.setFont(self.widget_font)

        # Create widgets
        self.update_rate_line_edit = QtGui.QLineEdit()
        self.update_rate_line_edit.setText(make_unicode(self.default_min_update_distance))
        self.update_rate_line_edit.setMaximumWidth((QFontMetrics(self.widget_font).width('01.23')))
        #self.update_rate_line_edit.setInputMask('00.0')
        self.update_rate_label = QtGui.QLabel('Update Distance')
        self.update_rate_units_label = QtGui.QLabel('(meters)')
        self.spacer1 = QtGui.QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.spacer2 = QtGui.QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.fix_aspect_checkbox = QCheckBox()
        self.fix_aspect_checkbox.setText('Fix Aspect Ratio')
        self.fix_aspect_checkbox.setFont(self.widget_font)
        self.fix_aspect_checkbox.setChecked(True)
        self._fix_aspect_toggled(self.fix_aspect_checkbox.isChecked())

        self.update_rate_label.setFont(self.widget_font)
        self.update_rate_line_edit.setFont(self.widget_font)
        self.update_rate_units_label.setFont(self.widget_font)

        # Add widgets to layout
        main_layout = QtGui.QVBoxLayout(self)
        main_layout.addWidget(self.map_view)

        bottom_row_layout = QtGui.QHBoxLayout()
        bottom_row_layout.addWidget(self.update_rate_label)
        bottom_row_layout.addWidget(self.update_rate_line_edit)
        bottom_row_layout.addWidget(self.update_rate_units_label)
        bottom_row_layout.addSpacerItem(self.spacer1)
        bottom_row_layout.addWidget(self.fix_aspect_checkbox)
        bottom_row_layout.addSpacerItem(self.spacer2)
        bottom_row_layout.addWidget(self.clear_map_button)

        main_layout.addLayout(bottom_row_layout)

        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)