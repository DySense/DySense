# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import yaml
import sys
import logging
import os

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QMetaObject, QObject, QEvent, Qt, Q_ARG
from PyQt4.QtGui import *

from dysense.gui.dysense_main_window_designer import Ui_main_window
from dysense.gui.sensor_view_widget import SensorViewWidget
from dysense.gui.controller_view_widget import ControllerViewWidget
from dysense.gui.extras_menu_widget import ExtrasMenuWidget
from dysense.gui.new_issue_popup import NewIssuePopupWindow
from dysense.gui.data_table_widget import DataTableWidget

from dysense.core.utility import pretty, make_unicode
from dysense.core.version import app_version

class DysenseMainWindow(QMainWindow, Ui_main_window):
    
    def __init__(self, presenter, sensor_metadata):
        
        QMainWindow.__init__(self)
        
        self.qt_settings = QtCore.QSettings("DySense", "DySenseUI")
        
        # Set up the user interface from Designer.
        self.setupUi(self)
        
        self.presenter = presenter
        self.sensor_metadata = sensor_metadata
   
        # Set logo
        main_logo = QtGui.QPixmap('../resources/horizontal_logo.png')
        main_logo = main_logo.scaled(140,40)      
        self.logo_label.setPixmap(main_logo)
        
        # Maintains list widget background and text color when focus is lost
        self.setStyleSheet( """QListWidget:item:selected:!disabled 
                            {  background: blue; color: white;}"""
                            )        
        
        # Local controller name at program startup.  Set only once when property is first accessed.
        self.initial_stored_controller_name = None
        
        # Set version to message center and as window title   
        QMainWindow.setWindowTitle(self, 'DySense ' + app_version)     
        
        # Associate sensor (controller_id, sensor_id) to its widget.
        self.sensor_to_widget = {}
    
        # Associate controller (controller_id) to its widget.
        self.controller_to_widget = {}
            
        #dictionaries for relating the controller info names to their corresponding line edits/labels        
        self.name_to_object =  {
                                #'session_name': self.session_line_edit,
                                }
        
        self.object_to_name =  {
                                #self.session_line_edit: 'session_name',                                                                       
                               }   
            
        # Lookup table of sensor views in the stacked widget
        # key - (controller_id, sensor id)
        # value - index in stacked widget
        self.sensor_view_stack = {}
               
        # Lookup table of controller views in the stacked widget
        # key - controller_id
        # value - index in stacked widget
        # menu page is always index 0 
        self.controller_view_stack = {}
        
        # Lookup table of sensor 'items' in the list widget
        # key - tuple of (controller id, sensor id)
        # value - row position index of list item
        self.sensor_to_list_row = {}
        
        # Lookup table of controller 'items' in the list widget
        # key - controller id
        # value - row position index of list item
        self.controller_to_list_row = {}
        
        # View associated with local controller. 
        self.local_controller_view = None
        
        # Create menu that includes extra functionality.
        self.extras_menu = ExtrasMenuWidget(self.presenter, self)
        self.stacked_widget.addWidget(self.extras_menu)
        
        # Create widget for showing all sensor data at once.
        self.sensor_data_table = DataTableWidget()
        self.stacked_widget.addWidget(self.sensor_data_table)
        
        # Load icons that will be used in sensor list widget.
        self.not_setup_icon = QtGui.QIcon('../resources/sensor_status_icons/neutral_paused.png')
        
        # Load all sensor status icons in dict
        # example {'neutral': neutral_icon}
        self.sensor_status_icons = {}
        resources_directory = '../resources/sensor_status_icons'
        sensor_icon_file_names = ['not_setup', 'neutral', 'good', 'bad',
                                   'neutral_paused', 'good_paused', 'bad_paused']
        for file_name in sensor_icon_file_names:
            status_icon = QtGui.QIcon(os.path.join(resources_directory, file_name + '.png'))
            self.sensor_status_icons[file_name] = status_icon
                
        # Connect main command buttons
        self.menu_button.clicked.connect(self.menu_button_clicked)
        self.extras_button.clicked.connect(self.extras_button_clicked)
        
        self.sensor_list_widget.itemClicked.connect(self.list_item_clicked)
        
    @property
    def local_controller_name(self):
        stored_controller_name = self.qt_settings.value("local_controller_name")
        if stored_controller_name is None:
            stored_controller_name = "default"
            
        # Make it so the first name returned is always the name returned to prevent
        # the controller name from changing as the program is running.
        if self.initial_stored_controller_name is None:
            self.initial_stored_controller_name = stored_controller_name
            
        return make_unicode(self.initial_stored_controller_name)
        
    @local_controller_name.setter
    def local_controller_name(self, new_value):
        self.qt_settings.setValue("local_controller_name", make_unicode(new_value))           
    
    def add_new_controller(self, controller_id, controller_info, is_local):
        
        self.create_new_controller_view(controller_id, controller_info, is_local)

        self.refresh_sensor_list_widget()
    
    def create_new_controller_view(self, controller_id, controller_info, is_local):
        
        new_controller_view = ControllerViewWidget(self.presenter, self, controller_id, controller_info, self.sensor_metadata)
        
        # Add the sensor view widget to the stack
        self.stacked_widget.addWidget(new_controller_view)
            
        # Create connection between controller ID and stacked widget index 
        self.controller_view_stack[controller_id] = self.stacked_widget.indexOf(new_controller_view)
        
        # Create connection between controller ID and view widget
        self.controller_to_widget[controller_id] = new_controller_view
        
        # Show new view
        self.show_controller(controller_id)
    
        if is_local:
            self.local_controller_view = new_controller_view
    
    def add_new_sensor(self, controller_id, sensor_id, sensor_info):
        
        self.create_new_sensor_view(controller_id, sensor_id, sensor_info)
        
        self.refresh_sensor_list_widget()
        
        # Now that sensor is in list widget update it's info.
        self.update_all_sensor_info(controller_id, sensor_id, sensor_info)
        
        # Add sensor row to widget that shows all sensor data.
        self.sensor_data_table.add_sensor(sensor_id, sensor_info)
    
    def create_new_sensor_view(self, controller_id, sensor_id, sensor_info):
        
        new_sensor_view = SensorViewWidget(controller_id, sensor_info, self.presenter, self)
        
        # Add the sensor view widget to the stack
        self.stacked_widget.addWidget(new_sensor_view)
            
        # Add the widget to sensor_view_stack dict - currently used in show_sensor
        self.sensor_view_stack[(controller_id, sensor_id)] = self.stacked_widget.indexOf(new_sensor_view)
        
        # Add widget instance and index to the sensor_info
        self.sensor_to_widget[(controller_id, sensor_id)] = new_sensor_view
            
    def refresh_sensor_list_widget(self):
        
        self.recalculate_list_widget_ordering()

        self.sensor_list_widget.clear()
        
        for controller_id, row_idx in self.controller_to_list_row.items():
            controller_list_item = QListWidgetItem()
            controller_list_item.setText(controller_id)
            font = QtGui.QFont()
            font.setBold(True)
            font.setUnderline(True)
            controller_list_item.setFont(font)
            self.sensor_list_widget.insertItem(row_idx, controller_list_item)
        
        for (controller_id, sensor_id), row_idx in self.sensor_to_list_row.items():
            self.sensor_list_widget.insertItem(row_idx, sensor_id)
            
        # Update list for things like paused status and color.
        for (controller_id, sensor_id) in self.sensor_to_list_row:
            self.update_sensor_list_widget(controller_id, sensor_id)
        for controller_id in self.controller_to_list_row:
            self.update_controller_in_sensor_list_widget(controller_id)
            
        self.adjust_sensor_list_size()
        
    def adjust_sensor_list_size(self):
        
        # Adjust widget to account for width of new text.
        min_list_width = 150
        max_list_width = self.width() * 0.25
        required_width = self.sensor_list_widget.sizeHintForColumn(0) + 2 * self.sensor_list_widget.frameWidth()
        required_width = max(required_width, min_list_width)
        required_width = min(required_width, max_list_width)
        #required_height = self.sensor_list_widget.sizeHintForRow(0) * self.sensor_list_widget.count()
        
        # Set minimum width which since sizeHint is fixed should set the actual width.
        self.sensor_list_widget.setMinimumWidth(required_width)

    def resizeEvent(self, event_info):
        
        self.adjust_sensor_list_size()
            
    def recalculate_list_widget_ordering(self):
        
        # The next row index in the list widget to assign to a controller or sensor.
        next_row_idx = 0
        
        # Reset list index lookups.
        self.controller_to_list_row = {}
        self.sensor_to_list_row = {}
        
        # Alphabetize controller IDs (names) while keeping the local controller first.
        remote_controller_ids = [c_id for c_id in self.controller_to_widget if c_id != self.presenter.local_controller['id']]
        remote_controller_ids = sorted(remote_controller_ids)
        sorted_controller_ids = [self.presenter.local_controller['id']] + remote_controller_ids
        
        for controller_id in sorted_controller_ids:
            self.controller_to_list_row[controller_id] = next_row_idx
            next_row_idx += 1
        
            matching_sensor_ids = [s_id for (c_id, s_id) in self.sensor_to_widget if c_id == controller_id]
            sorted_sensor_ids = sorted(matching_sensor_ids)
            for sensor_id in sorted_sensor_ids:
                self.sensor_to_list_row[(controller_id, sensor_id)] = next_row_idx
                next_row_idx += 1
        
            # Increment again to put a space in between controllers.
            next_row_idx += 1
        
    def update_sensor_list_widget(self, controller_id, sensor_id):
        
        sensor = self.presenter.sensors[(controller_id, sensor_id)]
        sensor_name = sensor['sensor_id']

        row = self.sensor_to_list_row[(controller_id, sensor_id)]
        item = self.sensor_list_widget.item(row)
        #item.setTextAlignment(Qt.AlignVCenter)
        item.setText(sensor_name)
        status_icon = self.get_sensor_status_icon(sensor['overall_health'], sensor['sensor_paused'], sensor['connection_state'])
        item.setIcon(status_icon)
        
    def get_sensor_status_icon(self, sensor_health, is_paused, connection_state):
        
        if connection_state == 'closed' or sensor_health == 'N/A':
            icon_name = 'not_setup'
        else:
            icon_name = sensor_health            
            if is_paused:
                icon_name += '_paused'
                
        try:
            icon = self.sensor_status_icons[icon_name]
        except KeyError:
            icon = None
            
        return icon
        
    def update_controller_in_sensor_list_widget(self, controller_id):
        
        # TODO add icons for controller for session
        #controller = self.presenter.controllers[controller_id]
        pass
        
    def list_item_clicked(self, item):
                
        #item name = text of item in display list, which is the same as the sensor name
        row_idx = self.sensor_list_widget.currentRow()

        # Check if it was a sensor that was clicked on.
        for (controller_id, sensor_id), value in self.sensor_to_list_row.items():
            if value == row_idx:
                self.presenter.new_sensor_selected(controller_id, sensor_id)
                return 
               
        # Check if it was a controller that was clicked on. 
        for controller_id, value in self.controller_to_list_row.items():
            if value == row_idx:
                self.presenter.new_controller_selected(controller_id)
                return 
      
    def show_sensor(self, controller_id, sensor_id):
        
        self.stacked_widget.setCurrentIndex(self.sensor_view_stack[(controller_id, sensor_id)])
        
        self.presenter.update_active_sensor(controller_id, sensor_id)
      
    def show_controller(self, controller_id):
        
        self.stacked_widget.setCurrentIndex(self.controller_view_stack[controller_id])
        
        self.presenter.active_controller = controller_id
        
    def show_main_menu(self):
        
        if self.local_controller_view is not None:
            self.stacked_widget.setCurrentWidget(self.local_controller_view)
        
    def show_sensor_data_table(self):
        
        self.stacked_widget.setCurrentWidget(self.sensor_data_table)
        
    def menu_button_clicked(self):
        
        self.show_main_menu()
        
        # Deselect list widget items so health color shows
        self.deselect_all_sensor_items()
            
    def extras_button_clicked(self):
        
        self.stacked_widget.setCurrentWidget(self.extras_menu)
        
        # Deselect list widget items so health color shows
        self.deselect_all_sensor_items()
        
    def deselect_all_sensor_items(self):
           
        for i in range(self.sensor_list_widget.count()):
            item = self.sensor_list_widget.item(i)
            self.sensor_list_widget.setItemSelected(item, False)

    def display_message(self, message):
        
        # TODO - support multiple controllers
        self.local_controller_view.add_message(message)

    def remove_controller(self, controller_id):
        pass # TODO
        
    def update_all_sensor_info(self, controller_id, sensor_id, sensor_info):        

        for key in sensor_info:        
            self.update_sensor_info(controller_id, sensor_id, key, sensor_info[key])   
         
    def update_sensor_info(self, controller_id, sensor_id, info_name, value):

        sensor_view = self.sensor_to_widget[(controller_id, sensor_id)]             
        sensor_view.update_sensor_view(info_name, value)

        if info_name in ['overall_health', 'sensor_paused', 'connection_state']:
            self.update_sensor_list_widget(controller_id, sensor_id)  
        
    def remove_sensor(self, controller_id, sensor_id):
                
        self.show_main_menu()
        
        # remove sensor from appropriate dictionaries
        del self.sensor_to_widget[(controller_id, sensor_id)]
        del self.sensor_view_stack[(controller_id, sensor_id)]
        
        self.refresh_sensor_list_widget()
        
        # Remove row from table that shows all sensor data.
        self.sensor_data_table.remove_sensor(sensor_id)
    
    def show_new_sensor_data(self, controller_id, sensor_id, data):
                
        # if the passed sensor is active, call function in sensor_viewer to update data visualization
        # data visualization
        if (controller_id, sensor_id) == (self.presenter.active_controller_id, self.presenter.active_sensor_id):
            
            sensor_view = self.sensor_to_widget[(controller_id, sensor_id)]
                        
            sensor_view.update_data_visualization(data)
            
        # TODO support multiple controllers
        self.sensor_data_table.refresh_sensor_data(sensor_id, data)
            
    def append_sensor_message(self, controller_id, sensor_id, text):

        sensor_view = self.sensor_to_widget[(controller_id, sensor_id)]  
        sensor_view.display_message(make_unicode(text).strip('[]'), True)
        
    def show_user_message(self, message, level):
        
        popup = QtGui.QMessageBox()
        font = QtGui.QFont()
        font.setPointSize(13)
        popup.setFont(font)
        
        if level == logging.CRITICAL:
            level_text = "Critical Error"
            icon = QStyle.SP_MessageBoxCritical
        elif level == logging.ERROR:
            level_text = "Error"
            icon = QStyle.SP_MessageBoxWarning
        elif level == logging.WARN:
            level_text = "Warning"
            icon = QStyle.SP_MessageBoxWarning
        elif level == logging.INFO:
            level_text = "Info"
            icon = QStyle.SP_MessageBoxInformation
        else:
            return # not a level we need to show
            
        popup.setText(make_unicode(message))
        popup.setWindowTitle('{}'.format(level_text))
        popup.setWindowIcon(popup.style().standardIcon(icon))
        
        popup.exec_()
        
    def update_all_controller_info(self, controller_id, controller_info):
        
        controller_view_widget = self.controller_to_widget[controller_id]
        
        controller_view_widget.update_info(controller_info)
        
    def refresh_current_issues(self, current_issues):
        
        # TODO support multiple controllers
        self.local_controller_view.refresh_current_issues(current_issues)
                
    def notify_new_issue(self, issue_info):
                
        self.new_issue_popup = NewIssuePopupWindow()
        #self.new_issue_popup.setModal(True)
        self.new_issue_popup.show()
        