# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import islice

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
        
        # Default value for minimum amount of time to wait before drawing map updates.
        self.default_min_update_period = 0.5
        
        # Actual widget where points are drawn.
        self.map_view = MapView(self)
        
        # Use to combine multiple sources into one position.
        self.source_filter = MapSourceFilter(self.default_min_update_period)
        
        # Use to move between different coordinate frames.
        self.converter = CoordinateConverter()
        
        # List of MapPositions. These are converted to pixel coordinates and drawn on the map.
        self.positions = []
   
        # Setup interface after map has been created.
        self._setup_ui()
        
        # Colors of different points.
        self.normal_point_color = Qt.green
        self.start_point_color = Qt.blue
        self.last_point_color = Qt.red
        
        # Connect signals to slots
        self.clear_map_button.clicked.connect(self._clear_map_button_clicked)
        self.update_rate_line_edit.textChanged.connect(self._update_rate_changed)
        
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
            return False
        
        map_position = self.converter.convert_to_map_position(filtered_position)
        self.positions.append(map_position)
        
        need_to_rescale_map = self.converter.need_to_calculate_pixel_scale(map_position)
        
        if need_to_rescale_map:
            self._calculate_new_pixel_scale()
            self._redraw_all_positions()
        else:
            self._draw_new_position(map_position)
        
        return True # position drawn successfully
        
    def clear_map(self):
        '''Delete all saved positions and everything drawn on map.'''
        self.positions = []
        self.converter.reset_bounds()
        self.source_filter.reset()
        self.map_view.reset_map()
        
    def _calculate_new_pixel_scale(self):
        
        self.converter.calculate_new_pixel_scale(self.map_view)
        
        self.map_view.update_pixels_per_meter(self.converter.pixels_per_meter_x)
        
    def _draw_new_position(self, position):
        '''Convert MapPosition to pixels and add to map.'''

        if len(self.positions) == 0:
            self._draw_start_position(position)
        else:
            self.map_view.update_last_point_color(self.normal_point_color)
            self._draw_map_position(position, self.last_point_color)
        
    def _redraw_all_positions(self):
        '''Clear map and re-draw all saved positions.'''
        self.map_view.reset_map()
        
        if len(self.positions) == 0:
            return
        
        self._draw_start_position(self.positions[0])
        
        for position in islice(self.positions, 1, None):
            self._draw_map_position(position, self.normal_point_color)
    
        self.map_view.update_last_point_color(self.last_point_color)
    
    def _draw_start_position(self, position):
        
        self._draw_map_position(position, self.start_point_color, radius=10, importance=1)
    
    def _draw_map_position(self, position, color, radius=7, importance=0):
        
        x, y = self.converter.convert_to_pixel_position(position)
        self.map_view.draw_point(x, y, color, radius, importance)
    
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
            update_rate = float(self.update_rate_line_edit.text())
            self.source_filter.min_update_period = 1.0 / update_rate
        except (ZeroDivisionError, ValueError):
            pass
        
    def _setup_ui(self):
        
        self.widget_font = QFont('mapping_font', pointSize=12)
        
        self.clear_map_button = QtGui.QPushButton('Clear Map')
        self.clear_map_button.setFont(self.widget_font)     
        
        # Create widgets
        self.update_rate_line_edit = QtGui.QLineEdit()
        self.update_rate_line_edit.setText(make_unicode(1 / self.default_min_update_period))
        self.update_rate_line_edit.setMaximumWidth((QFontMetrics(self.widget_font).width('1.23')))
        self.update_rate_line_edit.setInputMask('0.0')
        self.update_rate_label = QtGui.QLabel('Update Rate')
        self.update_rate_units_label = QtGui.QLabel('Hz')
        self.spacer = QtGui.QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        
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
        bottom_row_layout.addSpacerItem(self.spacer)
        bottom_row_layout.addWidget(self.clear_map_button)

        main_layout.addLayout(bottom_row_layout)
        
        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)