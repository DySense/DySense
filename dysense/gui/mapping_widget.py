# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import sys

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class MappingWidget(QtGui.QWidget):
    
    def __init__(self, presenter):
        '''Constructor'''
        QtGui.QWidget.__init__(self)
        
        self.presenter = presenter
        
        self.map_view = MapView(self)
        
        # Saved positions (northing, easting)
        self.positions = []
        
        # Minimum time to wait before adding new point.
        self.min_update_period = 0.5
        
        # Convert lat/long to meters. Set once receive first latitude.
        self.meters_per_deg_lat = float('NaN')
        self.meters_per_deg_long = float('NaN')
        
        # Set to true when need to use the next latitude to calculate a new scale between degrees and meters.
        self.need_to_calculate_deg_scale = True
        
        # Convert between meters and pixels
        self.pixels_per_meter_x = 0
        self.pixels_per_meter_y = 0
        
        self._reset_bounds()
        
        self._setup_ui()
        
    def _setup_ui(self):
        
        self.clear_map_button = QtGui.QPushButton('Clear Map')        
        
        # Create widgets
        self.update_rate_line_edit = QtGui.QLineEdit()
        self.update_rate_line_edit.setMaxLength(3)
        self.update_rate_line_edit.setInputMask('0.00')        
        self.update_rate_label = QtGui.QLabel('Update Rate')
        self.update_rate_units_label = QtGui.QLabel('Hz')
        self.spacer = QtGui.QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        
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
        
        #bottom_row_layout.setContentsMargins(0, 0, 0, 0)
        
        # Want the map to take up as much space as possible
        self.map_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Connect signals to slots
        self.clear_map_button.clicked.connect(self.clear_map_button_clicked)
        self.update_rate_line_edit.editingFinished.connect(self.update_rate_changed)

        self.update_rate_line_edit.setText('2')
        
    def resizeEvent(self, *args, **kwargs):
        self.redraw_map()
        
    def redraw_map(self):
        
        self.map_view.resize_scene_to_viewport()
        
        self._calculate_new_pixel_scale()
    
    def clear_map_button_clicked(self):
        
        question = "Are you sure you want to clear the map?"
        if not self.presenter.view.confirm_question(question):
            return
        
        self.clear_map()
                
    def update_rate_changed(self):
        try:
            update_rate = float(self.update_rate_line_edit.text())
            self.min_update_period = 1.0 / update_rate
        except ZeroDivisionError:
            pass
        
    def update_for_new_position(self, controller_id, sensor_id, utc_time, sys_time, data):

        try:
            latitude, longitude = data[:2]
        except ValueError:
            return # not enough data provided

        expected_number_of_sources = len(self.presenter.local_controller['position_sources'])
        
        if expected_number_of_sources == 0:
            return # No selected source(s), this data is likely brand new or old.
        if expected_number_of_sources > 1:
            # More than one source so need to average into a single position
            latitude, longitude = self._try_merge_positions(latitude, longitude)
            if latitude is None:
                return # Need to wait for newer data from another source.
        else:
            # Just one sensor so can use it's position directly.
            pass
            
        self._new_position(latitude, longitude)
            
    def _reset_bounds(self):
        '''Set bounds to extremes so they will be overwritten by next valid position'''
        self.min_northing = sys.float_info.max
        self.max_northing = -sys.float_info.max
        self.min_easting = sys.float_info.max
        self.max_easting = -sys.float_info.max
            
    def _new_position(self, latitude, longitude):
            
        if self.need_to_calculate_deg_scale:
            self.meters_per_deg_lat = (111132.92-559.82*math.cos(2*latitude*math.pi / 180)+1.175*math.cos(4*latitude*math.pi / 180))
            self.meters_per_deg_long = (111412.84*math.cos(latitude*math.pi / 180) - 93.5*math.cos(3*latitude*math.pi / 180))
            self.need_to_calculate_deg_scale = False
            
        # Convert to meters since we need to plot in 2D plane and meters are easy for user to understand.
        north_meters = self.meters_per_deg_lat * latitude
        east_meters = self.meters_per_deg_long * longitude
        
        new_position = (north_meters, east_meters)
        
        self.positions.append(new_position)

        # If new position is outside the old bounds then we'll need to calculate a new meters -> pixel scaling.
        need_to_rescale = False

        if north_meters < self.min_northing:
            self.min_northing = north_meters
            need_to_rescale = True
        if north_meters > self.max_northing:
            self.max_northing = north_meters
            need_to_rescale = True
        if east_meters < self.min_easting:
            self.min_easting = east_meters
            need_to_rescale = True
        if east_meters > self.max_easting:
            self.max_easting = east_meters
            need_to_rescale = True

        if need_to_rescale:
            self._calculate_new_pixel_scale()
            self._redraw_all_positions()
        else:
            self._draw_position(new_position)
            
        # TODO
        #elif self.isVisible():
        #    self._draw_position(new_position)
        #else:
        #    # Wait until map is visible again and the point will be drawn then.
        #    pass
        
    def _calculate_new_pixel_scale(self):
        
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
            
    def _redraw_all_positions(self):
        
        self.map_view.reset_map()
        
        for position in self.positions:
            self._draw_position(position)
            
        self.map_view.update_scale_bar(self.pixels_per_meter_x)
        
    def _draw_position(self, position):
        
        northing, easting = position
        
        x_pix = (easting - self.min_easting) * self.pixels_per_meter_x
        y_pix = (northing - self.min_northing) * self.pixels_per_meter_y
            
        self.map_view.draw_point(x_pix, y_pix)
        
    def _try_merge_positions(self, latitude, longitude):
        
        # TODO filter by time and source
        return latitude, longitude
    
    def clear_map(self):
        
        self.positions = []
        self._reset_bounds()
        self.map_view.reset_map()

class MapView(QtGui.QGraphicsView):
    
    def __init__(self, parent):
        '''Constructor'''
        QtGui.QGraphicsView.__init__(self, parent)
        
        self.parent = parent
        
        self.setScene(QtGui.QGraphicsScene(self))
        self.resize_scene_to_viewport()
        
        # Radius of points in pixels
        self.point_radius = 7
        
        # Turn off the scroll bars
        self.setVerticalScrollBarPolicy(1)
        self.setHorizontalScrollBarPolicy(1)
        
        self.last_point = None
        
        self.reset_map()
        
    @property
    def drawable_width(self):
        return self.sceneRect().size().width() - 30
        
    @property
    def drawable_height(self):
        return self.sceneRect().size().height() - 50
        
    def map_resized(self):
               
        x_len, y_len = self.scene_size()
        self.center_x = x_len / 2.0
        self.center_y = y_len / 2.0
               
    def reset_map(self):
        
        self.scene().clear()
        
        self.map_resized()
        
    def resize_scene_to_viewport(self):
        self.setSceneRect(QtCore.QRectF(self.viewport().rect()))    
        
    def scene_size(self):
        
        scene_size = self.sceneRect().size()
        return [scene_size.width(), scene_size.height()]  
     
    def draw_point(self, x_pix, y_pix):
        
        if math.isnan(x_pix):
            x_pix = self.center_x
            
        if math.isnan(y_pix):
            y_pix = self.center_y
        
        new_point = self.scene().addEllipse(x_pix, y_pix, self.point_radius, self.point_radius)
        
        if self.last_point is None:
            new_point.setBrush(Qt.blue)
        else:
            new_point.setBrush(Qt.green)
            
        self.last_point = new_point 
            
    def update_scale_bar(self, pixels_per_meter):        
        '''Update length of scale bar based on the pixels_per_meter ratio'''  
         
        scale_length = 100 # pixels
        y_pos_scale = 2 * self.center_y - 30
        x_pos1_scale = self.center_x - (scale_length / 2)
        x_pos2_scale = self.center_x + (scale_length / 2)
        scale_value = (scale_length / pixels_per_meter)
        
        vert_line_length = 15        
        
        pen = QPen(Qt.black,3)
        
        # Set horizontal lines of scale bar
        line1 = QLineF(x_pos1_scale, y_pos_scale,x_pos2_scale , y_pos_scale)
        line_item1 = QGraphicsLineItem(line1, scene=self.scene())
        line_item1.setPen(pen)

        # Set vertical lines of scale bar
        line2 = QLineF(x_pos1_scale, y_pos_scale,x_pos1_scale, y_pos_scale-vert_line_length)
        line3 = QLineF(x_pos2_scale, y_pos_scale-vert_line_length,x_pos2_scale, y_pos_scale)
        line_item2 = QGraphicsLineItem(line2, scene=self.scene())
        line_item3 = QGraphicsLineItem(line3, scene=self.scene())
        line_item2.setPen(pen)
        line_item3.setPen(pen)
        
        x_pos_text = self.center_x + 30 + (scale_length / 2)
        y_pos_text = 2 * self.center_y - 50
        
        scale_text = QGraphicsTextItem(scene = self.scene())   
        scale_text.setPlainText('%.2f Meters' % scale_value)    
        scale_text.adjustSize()
        scale_text.setPos(x_pos_text, y_pos_text)
        
        