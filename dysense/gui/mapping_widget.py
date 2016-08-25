# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import re

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class MappingWidget(QtGui.QWidget):
    
    def __init__(self, presenter):
        '''Constructor'''
        QtGui.QWidget.__init__(self)

        self.view = View(self)
        
        self.presenter = presenter
        
        self.setContentsMargins(0,0,0,0)
        
        # list of tuples of the controller and sensor ids that have been sent for position data
        self.data_sources = []
        
        # list of tuples of lat, long, and sys_time
        self.position_data_degs = []        
        self.source_count = 0
        
        self.active = True
        
        self.clear_map_button = QtGui.QPushButton('Clear Map')        
        
        # Create items
        self.update_rate_line_edit = QtGui.QLineEdit()
        self.update_rate_line_edit.setMaxLength(3)
        self.update_rate_line_edit.setInputMask('0.00')        
        self.update_rate_line_edit.setFixedWidth(60)
        self.update_rate_label = QtGui.QLabel('Update Rate')
        self.spacer = QtGui.QSpacerItem(1,1, QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        self.update_rate_label.setToolTip('Hz')
        self.update_rate_line_edit.setToolTip('Hz')
        
        # add items to layouts
        hlayout = QtGui.QHBoxLayout()
        hlayout.addWidget(self.update_rate_label)
        hlayout.addWidget(self.update_rate_line_edit)
        hlayout.addSpacerItem(self.spacer)
        hlayout.addWidget(self.clear_map_button)
        
        vlayout = QtGui.QVBoxLayout(self)
        vlayout.addWidget(self.view)
        vlayout.addLayout(hlayout)
        
        vlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setContentsMargins(0, 0, 0, 0)
        
               
        # make connections
        self.clear_map_button.clicked.connect(self.clear_map_button_clicked)
        self.update_rate_line_edit.textChanged.connect(self.update_rate_changed)
        
        # set default update rate to 2
        self.update_rate_line_edit.setText('2')
        
        self.set_size()
        self.initial_setup()    
        
    def set_size(self):
        self.view.setSceneRect(QtCore.QRectF(self.view.viewport().rect()))    
    
    def initial_setup(self):
        self.view.setup()
        
    def clear_map_button_clicked(self):
        pass
                
        
    def update_rate_changed(self):
        try:
            self.update_rate = float(self.update_rate_line_edit.text())
            self.update_time = 1.0/self.update_rate
            
        except ValueError:
            pass        
        
    def new_data_recieved(self, controller_id, sensor_id, source_type, utc_time, sys_time, data):        

        # add the first position source to data sources list
        if self.source_count == 0:
            self.data_sources.append((controller_id, sensor_id))           
            self.source_count += 1
            
            # add the lat, long, and sys time for the first position data
            self.position_data_degs.append((data[0],data[1],sys_time))
            
            
            # calculate the degrees to centimeters scale factors with initial latitude
            self.cm_per_deg_lat = (111132.92-559.82*math.cos(2*data[0]*math.pi / 180)+1.175*math.cos(4*data[0]*math.pi / 180)) * 100.0
            self.cm_per_deg_long = (111412.84*math.cos(data[0]*math.pi / 180) - 93.5*math.cos(3*data[0]*math.pi / 180)) * 100.0            
            return
        
        # only use one position source for now    
        if (controller_id, sensor_id) not in self.data_sources:
            return
        
        # ensure that enough time has passed from the last stored data to current data
        if sys_time - self.position_data_degs[-1][2] >= self.update_time:
            self.position_data_degs.append((data[0],data[1],sys_time))
            
            self.view.add_point()
            return
                

class View(QtGui.QGraphicsView):
    
    def __init__(self, parent):
        QtGui.QGraphicsView.__init__(self, parent)
        self.parent = parent
        self.setScene(QtGui.QGraphicsScene(self))
        self.setSceneRect(QtCore.QRectF(self.viewport().rect())) 
        
        # store tuples of the x y values of each point in cm.
        self.point_relative_cm = []
        
        # store tuples of the x y coordinates of each point in pixels
        self.point_coords_pix = []
        
        # tuples of x y cm values of cached points to be plotted when map is shown
        self.point_cache = []
        
        # scale factor pixels/centimeter
        self.pixels_per_cm = 2
        
        # radius of points
        self.point_radius = 7
        
        # turn off the scroll bars
        self.setVerticalScrollBarPolicy(1)
        self.setHorizontalScrollBarPolicy(1)
        
        self.last_point = self.scene().addEllipse(-10,10, self.point_radius,self.point_radius)
               
    
    
    def setup(self):
        x_len, y_len = self.scene_size()
        self.cen_x = x_len/2.0
        self.cen_y = y_len/2.0
        self.center = (self.cen_x, self.cen_y)
        
        self.point_relative_cm.append((0,0))
        self.draw_origin()
                
        self.set_scale()       
        
    def draw_origin(self):
        cen_x, cen_y = self.center
        elip = self.scene().addEllipse(cen_x,cen_y, 15,15)
        elip.setBrush(Qt.blue)
        
    def set_scene_rect(self):
        self.setSceneRect(QtCore.QRectF(self.viewport().rect()))    
        
    def scene_size(self):
        
        scene_size = self.sceneRect().size()
        return [scene_size.width(), scene_size.height()]
 
    def add_point(self):
        
        # get the 2 most recent lats and longs
        lat1 = self.parent.position_data_degs[-2][0]
        lng1 = self.parent.position_data_degs[-2][1]
        
        lat2 = self.parent.position_data_degs[-1][0]
        lng2 = self.parent.position_data_degs[-1][1]
        
        delta_lat = lat2 - lat1
        delta_lng = lng2 - lng1
                                
        # convert to centimeters. latitude = y axis, longitude = x axis        
        delta_x_cm = delta_lng * self.parent.cm_per_deg_long
        delta_y_cm = delta_lat * self.parent.cm_per_deg_lat
                
        last_x = self.point_relative_cm[-1][0]
        last_y = self.point_relative_cm[-1][1]
        
        new_x_cm = last_x + delta_x_cm
        new_y_cm = last_y + delta_y_cm
        
        # save all points for redraw function
        self.point_relative_cm.append((new_x_cm, new_y_cm))        
        
        # only plot points if map is shown. Otherwise store points in cache.
        if not self.parent.active:
            self.point_cache.append((new_x_cm, new_y_cm))
            return        
        
        # if map is shown:
        
        if len(self.point_cache):
            
            # plot all points in cache
            self.plot_points(self.point_cache)
            
            # empty cache
            del self.point_cache[:]
            
        # continue to plot points while map is shown
        self.plot_single_point((new_x_cm, new_y_cm))        
        self.check_bounds()    
     
    
    def plot_single_point(self,point):
        
        cen_x = self.center[0]
        cen_y = self.center[1]
        x_pix = point[0]*self.pixels_per_cm + cen_x
        y_pix = point[1]*self.pixels_per_cm + cen_y
        new_point = self.scene().addEllipse(x_pix,y_pix, self.point_radius,self.point_radius)
        new_point.setBrush(Qt.green) 
        self.point_coords_pix.append((x_pix,y_pix))
    
    # takes a list of tuples of coordinates in cm and plots them for current pixel scaling
    def plot_points(self, points):
                
        cen_x, cen_y = self.center        
        
        # plot the origin reference point
        self.draw_origin()
        
        for point in points:
            x_pix = point[0]*self.pixels_per_cm + cen_x
            y_pix = point[1]*self.pixels_per_cm + cen_y
            new_point = self.scene().addEllipse(x_pix,y_pix, self.point_radius,self.point_radius)
            new_point.setBrush(Qt.green)
            self.point_coords_pix.append((x_pix,y_pix))            
    
    
    def check_bounds(self):
        
        current_x_max, current_x_min, current_y_max, current_y_min = self.get_bounds()       
                                    
        x_bound, y_bound = self.scene_size()                  
            
        if current_x_max >= x_bound - 30:
            self.refit()
                                             
        elif current_y_max >= y_bound - 30:
            self.refit()
            
        elif current_x_min <= 30:
            self.refit()
            
        elif current_y_min <= 30:
            self.refit()
                        
        else: 
            self.set_scale()
    
    def get_bounds(self): #NEW
        current_x_max = max(val[0] for val in self.point_coords_pix)
        current_x_min = min(val[0] for val in self.point_coords_pix)
        current_y_max = max(val[1] for val in self.point_coords_pix)
        current_y_min = min(val[1] for val in self.point_coords_pix)
        
        return current_x_max, current_x_min, current_y_max, current_y_min
    
    
    def refit(self):        
        # This function uses the 4 extremum of all logged position data points, max/min northing and max/min easting, and calculates the maximum pixels to meters ratio
        # while fitting them on the screen for all the possible origins. The origin with the largest ratio is selected and the corresponding ratio is set.
        self.refit_pixels_per_cm = 4
        self.all_origin_ratios = []
        reducing_scale_factor = 0.99
        origin_edge_space = 120
        
        x_len, y_len = self.scene_size()        
        
        self.possible_origins =  [
                                 (origin_edge_space, origin_edge_space),
                                 (x_len/2, origin_edge_space),
                                 (x_len-origin_edge_space, origin_edge_space),
                                 (origin_edge_space, y_len/2),
                                 (x_len/2, y_len/2),
                                 (x_len-origin_edge_space, y_len/2),
                                 (origin_edge_space, y_len-origin_edge_space),
                                 (x_len/2, y_len-origin_edge_space),
                                 (x_len-origin_edge_space, y_len-origin_edge_space)                         
                                 ]
        
        for origin in self.possible_origins:
            
            self.refit_pixels_per_cm = 4
            cen_x = origin[0]
            cen_y = origin[1]
            
            current_x_max_cm = max(val[0] for val in self.point_relative_cm)
            current_x_min_cm = min(val[0] for val in self.point_relative_cm)
            current_y_max_cm = max(val[1] for val in self.point_relative_cm)
            current_y_min_cm = min(val[1] for val in self.point_relative_cm)            
                        
            out_of_scene = True
            while out_of_scene == True:        
                 
                # max/min pix values are relative the current origin being tested
                x_max_pix = current_x_max_cm*self.refit_pixels_per_cm + cen_x
                x_min_pix = current_x_min_cm*self.refit_pixels_per_cm + cen_x
                y_max_pix = current_y_max_cm*self.refit_pixels_per_cm + cen_y                
                y_min_pix = current_y_min_cm*self.refit_pixels_per_cm + cen_y                                    
                
                    
                if x_max_pix >= x_len:
                    self.refit_pixels_per_cm = reducing_scale_factor * self.refit_pixels_per_cm
                    continue                      
                elif y_max_pix >= y_len:
                    self.refit_pixels_per_cm = reducing_scale_factor * self.refit_pixels_per_cm
                    continue
                elif x_min_pix <= 0:
                    self.refit_pixels_per_cm = reducing_scale_factor * self.refit_pixels_per_cm
                    continue
                elif y_min_pix <= 0:
                    self.refit_pixels_per_cm = reducing_scale_factor * self.refit_pixels_per_cm
                    continue
                else:
                    self.all_origin_ratios.append(self.refit_pixels_per_cm) 
                    out_of_scene = False
        
        # determine the new ratio and its corresponding origin        
        self.new_ratio = max(self.all_origin_ratios)
        origin_number = self.all_origin_ratios.index(self.new_ratio)     
        
        self.new_origin = self.possible_origins[origin_number]
        
        self.center = self.new_origin
        self.pixels_per_cm = self.new_ratio * 0.9
        self.draw_origin()
        
        self.scene().clear()
        
        del self.point_coords_pix[:]                 
           
        self.plot_points(self.point_relative_cm)
        
        # reset the scale for the new ratio
        self.set_scale()        
      
        
    # sets and updates the length scale based on the pixels_per_cm ratio    
    def set_scale(self):        
        
        scale_length = 100
        y_pos_scale = 2 * self.cen_y - 30
        x_pos1_scale = self.cen_x - (scale_length/2)
        x_pos2_scale = self.cen_x + (scale_length/2)
        scale_value = (scale_length / self.pixels_per_cm) / 100.0
        
        vert_line_length = 15        
        
        pen = QPen(Qt.black,3)
        
        # set horizontal lines of scale bar
        line1 = QLineF(x_pos1_scale, y_pos_scale,x_pos2_scale , y_pos_scale)
        line_item1 = QGraphicsLineItem(line1, scene=self.scene())
        line_item1.setPen(pen)

        
        # set vertical lines of scale bar
        line2 = QLineF(x_pos1_scale, y_pos_scale,x_pos1_scale, y_pos_scale-vert_line_length)
        line3 = QLineF(x_pos2_scale, y_pos_scale-vert_line_length,x_pos2_scale, y_pos_scale)
        line_item2 = QGraphicsLineItem(line2, scene=self.scene())
        line_item3 = QGraphicsLineItem(line3, scene=self.scene())
        line_item2.setPen(pen)
        line_item3.setPen(pen)
        
        x_pos_text = self.cen_x + 30 + (scale_length / 2)
        y_pos_text = 2 * self.cen_y - 50
        
        scale_text = QGraphicsTextItem(scene = self.scene())   
        scale_text.setPlainText('%.2f Meters' % scale_value)    
        scale_text.adjustSize()
        scale_text.setPos(x_pos_text, y_pos_text)
        
        