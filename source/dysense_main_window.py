# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import yaml
import sys
import logging
import os

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QMetaObject, QObject, QEvent, Qt, Q_ARG
#from PyQt4.QtGui import QMainWindow, QColor, QWidget, QFileDialog
from PyQt4.QtGui import *
from dysense_main_window_designer import Ui_MainWindow
from sensor_view_widget import SensorViewWidget
from new_issue_popup import NewIssuePopupWindow
from utility import pretty, open_directory_in_viewer, make_unicode

class DysenseMainWindow(QMainWindow, Ui_MainWindow):
    
    def __init__(self, presenter):
        
        QMainWindow.__init__(self)
        
        self.qt_settings = QtCore.QSettings("DySense", "DySenseUI")
        
        self.presenter = presenter        
        
                
        # Set up the user interface from Designer.
        self.setupUi(self)
        
        #load sensor metadata
        with open("../metadata/sensor_metadata.yaml", 'r') as stream:
            self.sensor_metadata = yaml.load(stream)
        
        #set logo
        main_logo = QtGui.QPixmap('../resources/horizontal_logo.png')
        main_logo = main_logo.scaled(140,40)      
        self.logo_label.setPixmap(main_logo)
        
        # Add a feature that when the logo is double clicked it brings up the most recent session directory.
        self.logo_label.mouseDoubleClickEvent = self.logo_double_clicked
        
        # Maintains list widget background and text color when focus is lost
        self.setStyleSheet( """QListWidget:item:selected:!disabled 
                            {  background: blue; color: white;}"""
                            )        
        
        # Setup current issue table.
        issue_table_font = QtGui.QFont()
        issue_table_font.setPointSize(12)
        self.current_issues_table.setFont(issue_table_font)
        self.current_issues_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.current_issues_table.cellClicked.connect(self.current_issue_clicked_on)
        
        # Local controller name at program startup.  Set only once when property is first accessed.
        self.initial_stored_controller_name = None
        
        #set version number
        # TODO the version from metadata should be the 'controller' version once
        # we support multiple of those and the GUI version should come from ui_settings.py
        # Set version to message center and as window title
        version = self.sensor_metadata.get('version', 'No Version Number')        
        QMainWindow.setWindowTitle(self, 'DySense Version ' + version)     
        self.main_message_center_text_edit.setText('Version ' + version)
        
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
            
        self.settings_name_to_object = {
                                        'base_out_directory': self.output_directory_line_edit,
                                        'operator_name': self.operator_name_line_edit,
                                        'platform_type': self.platform_type_line_edit,
                                        'platform_tag': self.platform_id_line_edit,
                                        'experiment_id': self.experiment_id_line_edit,
                                        'surveyed': self.surveyed_check_box                                     
                                        }   
        
        #Lookup table of sensor views in the stacked widget
        #key - (controller_id, sensor id)
        #value - index in stacked widget
        self.sensor_view_stack = {}
               
        #Lookup table of controller views in the stacked widget
        #key - controller_id
        #value - index in stacked widget
        #menu page is always index 0 
        self.controller_view_stack = {}
        
        #Lookup table of sensor 'items' in the list widget
        #key - tuple of (controller id, sensor id)
        #value - row position index of list item
        self.sensor_to_list_row = {}
        
        #Lookup table of controller 'items' in the list widget
        #key - controller id
        #value - row position index of list item
        self.controller_to_list_row = {}
        
        # Connect controller setting line edits
        self.controller_name_line_edit.editingFinished.connect(self.controller_name_changed)
        self.output_directory_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.operator_name_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.platform_type_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.platform_id_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.experiment_id_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.surveyed_check_box.clicked.connect(self.controller_setting_changed_by_user)
        
        # Connect output directory file dialog button
        self.output_directory_tool_button.clicked.connect(self.output_directory_tool_button_clicked)
        
        #Set fields not to be edited by user as read only
        self.main_message_center_text_edit.setReadOnly(True)
        
                
        #Connect main command buttons
        self.menu_button.clicked.connect(self.menu_button_clicked)
        self.clear_main_message_center_button.clicked.connect(self.clear_main_message_center_button_clicked)
        self.ack_all_issues_button.clicked.connect(self.ack_all_issues_button_clicked)
        
        #Connect sensor control buttons
        self.setup_sensors_button.clicked.connect(self.setup_sensors_button_clicked)
        self.start_session_button.clicked.connect(self.start_session_button_clicked)
        self.pause_sensors_button.clicked.connect(self.pause_sensors_button_clicked)
        self.resume_sensors_button.clicked.connect(self.resume_sensors_button_clicked)
        self.end_session_button.clicked.connect(self.end_session_button_clicked)
        self.close_sensors_button.clicked.connect(self.close_sensors_button_clicked)

        #Config buttons
        self.select_config_tool_button.clicked.connect(self.select_config_tool_button_clicked)
        self.load_config_button.clicked.connect(self.load_config_button_clicked)
        self.save_config_button.clicked.connect(self.save_config_button_clicked)
        
        self.add_sensor_button.clicked.connect(self.add_sensor_button_clicked)
        self.select_sources_button.clicked.connect(self.select_sources_button_clicked)
        
        self.sensor_list_widget.itemClicked.connect(self.list_item_clicked)
        
        # Populate last saved config file so user doesn't always have to select it.
        self.config_line_edit.setText(self.last_loaded_config_file_path)
                
    @property
    def last_saved_config_file_path(self):
        file_path = self.qt_settings.value("last_saved_config_file_path")
        if file_path is None:
            file_path = os.path.join(os.path.expanduser('~'), 'dysense_config.yaml')
        return make_unicode(file_path)
        
    @last_saved_config_file_path.setter
    def last_saved_config_file_path(self, new_value):
        self.qt_settings.setValue("last_saved_config_file_path", make_unicode(new_value))
      
    @property
    def last_loaded_config_file_path(self):
        file_path = self.qt_settings.value("last_loaded_config_file_path")
        return make_unicode(file_path)
        
    @last_loaded_config_file_path.setter
    def last_loaded_config_file_path(self, new_value):
        self.qt_settings.setValue("last_loaded_config_file_path", make_unicode(new_value))
        
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
      
    def setup_sensors_button_clicked(self):
        self.presenter.setup_all_sensors(only_on_active_controller=True)
        
    def start_session_button_clicked(self):
        self.presenter.send_controller_command('start_session', send_to_all_controllers=False) 
    
    def pause_sensors_button_clicked(self):
        self.presenter.pause_all_sensors(only_on_active_controller=True)
            
    def resume_sensors_button_clicked(self):
        self.presenter.resume_all_sensors(only_on_active_controller=True)                     
                               
    def end_session_button_clicked(self):
        self.presenter.end_session()
    
    def close_sensors_button_clicked(self):
        
        self.presenter.close_all_sensors(only_on_active_controller=True)
    
    def update_list_widget_color(self, health, controller_id, sensor_id):
        
        if sensor_id is None:
            row_idx = self.controller_to_list_row[controller_id]
        else:
            row_idx = self.sensor_to_list_row[(controller_id, sensor_id)]

        item = self.sensor_list_widget.item(row_idx)
        
        if health in ['N/A', 'neutral']:                      
            item.setBackgroundColor(QColor(255,255,255)) #white
                                    
        elif health == 'good':
            item.setBackgroundColor(QColor(12,245,0)) # light green
              
        elif health == 'bad':
            item.setBackgroundColor(QColor(250,145,145)) # light red
    
    def add_new_controller(self, controller_id, controller_info):
        
        # TODO
        #self.create_new_controller_view(controller_id, controller_info)
        self.controller_view_stack[controller_id] = 0 # TODO move to create new view
        self.controller_to_widget[controller_id] = self.menu_page
        
        self.refresh_sensor_list_widget()
    
    def add_new_sensor(self, controller_id, sensor_id, sensor_info):
        
        self.create_new_sensor_view(controller_id, sensor_id, sensor_info)
        
        self.refresh_sensor_list_widget()
        
        # Now that sensor is in list widget update it's info.
        self.update_all_sensor_info(controller_id, sensor_id, sensor_info)
    
    def create_new_sensor_view(self, controller_id, sensor_id, sensor_info):
        
        new_sensor_view = SensorViewWidget(controller_id, sensor_info, self.presenter, self)
        
        #Add the sensor view widget to the stack
        self.stacked_widget.addWidget(new_sensor_view)
            
        #Add the widget to sensor_view_stack dict - currently used in show_sensor
        self.sensor_view_stack[(controller_id, sensor_id)] = self.stacked_widget.indexOf(new_sensor_view)
        
        stack_index = self.stacked_widget.indexOf(new_sensor_view)
        
        #add widget instance and index to the sensor_info
        self.sensor_to_widget[(controller_id, sensor_id)] = new_sensor_view
            
    def add_sensor_button_clicked(self, sensor_info):
        
        self.presenter.add_sensor_requested()
            
    def select_sources_button_clicked(self):
        
        self.presenter.select_data_sources()        
        
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
        if sensor['sensor_paused']:
            sensor_name += ' (paused)'
        
        row = self.sensor_to_list_row[(controller_id, sensor_id)]
        item = self.sensor_list_widget.item(row)
        item.setText(sensor_name)
        
        self.update_list_widget_color(sensor['overall_health'], controller_id, sensor_id)
        
    def update_controller_in_sensor_list_widget(self, controller_id):
        
        # TODO tie color to issues.
        #controller = self.presenter.controllers[controller_id]
        self.update_list_widget_color('neutral', controller_id, sensor_id=None)
        
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
        
    def menu_button_clicked(self):
        #set menu page to the front of the stacked widget, menu page will always be index 0
        self.stacked_widget.setCurrentIndex(0)
        
        # deselect list widget items so health color shows   
        for i in range(self.sensor_list_widget.count()):
            item = self.sensor_list_widget.item(i)
            self.sensor_list_widget.setItemSelected(item, False)
        
    def clear_main_message_center_button_clicked(self):
        self.main_message_center_text_edit.clear()
        
    def ack_all_issues_button_clicked(self):
        self.presenter.acknowledge_issue({}, ack_all_issues=True)
    
    def output_directory_tool_button_clicked(self):
        output_directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        
        if not output_directory:
            return # User didn't select a directory.
        
        self.output_directory_line_edit.setText(output_directory)
        self.output_directory_line_edit.setModified(True)
        self.output_directory_line_edit.editingFinished.emit()
        
    def select_config_tool_button_clicked(self):
        
        config_file_path = QtGui.QFileDialog.getOpenFileName(self, 'Load Config', self.last_loaded_config_file_path, '*.yaml')

        if not config_file_path:
            return # User didn't select a config file.

        self.last_loaded_config_file_path = config_file_path
        
        # Also set this as the last saved so that when the user goes to save any updates
        # it defaults to this one.
        self.last_saved_config_file_path = config_file_path

        self.config_line_edit.setText(config_file_path)
        
    def load_config_button_clicked(self):

        config_file_path = self.config_line_edit.text()
        
        self.presenter.try_load_config(config_file_path)
 
    def save_config_button_clicked(self):

        config_file_path = QtGui.QFileDialog.getSaveFileName(self, 'Save Config', self.last_saved_config_file_path, '*.yaml')

        if not config_file_path:
            return # User doesn't want to save the file.
        
        self.last_saved_config_file_path = config_file_path
        
        # Also set this as the last loaded so that when user opens the app again this will be default.
        self.last_loaded_config_file_path = config_file_path
        
        self.presenter.try_save_config(config_file_path)
             
    def display_message(self, message):
        self.main_message_center_text_edit.append(message)
        
    def update_all_controller_info(self, controller_id, controller_info):

        for info_name, value in controller_info.iteritems():
            
            if info_name in self.name_to_object:
                obj = self.name_to_object[info_name]
                obj.setText(make_unicode(value))
                
            if info_name == 'id':
                self.controller_name_line_edit.setText(value)
                
            if info_name == 'session_active':
                self.session_value_label.setText('Active' if value else 'Not Started')
                
            if info_name == 'session_state':
                self.main_status_value_label.setText(make_unicode(pretty(value)))
            
            if info_name == 'settings':
                settings = value 
                for settings_name, settings_value in settings.iteritems():               
                                    
                    if settings_name == 'surveyed':
                        if make_unicode(settings_value).lower() == 'true':
                            self.surveyed_check_box.setChecked(True)
                        else:
                            self.surveyed_check_box.setChecked(False)
                        continue              
                    
                    if settings_name in self.settings_name_to_object:
                        obj = self.settings_name_to_object[settings_name]
                        obj.setText(make_unicode(settings_value))
            
    def controller_name_changed(self):
        
        if self.sender().isModified():
            self.presenter.controller_name_changed(self.controller_name_line_edit.text())
            self.sender().setModified(False)
            
    def controller_setting_changed_by_user(self):
        obj_ref = self.sender()  
        
        if isinstance(obj_ref, QLineEdit):
            if not obj_ref.isModified():
                return
            else:
                obj_ref.setModified(False)
        
        #the new value will be the text in the line edits, except when it is the surveyed checkbox. 
        new_value = self.sender().text()      
        
        for key in self.settings_name_to_object:
            if self.settings_name_to_object[key] == obj_ref:  
                setting_name = key
                                
                if setting_name == 'surveyed':
                    state = self.surveyed_check_box.isChecked()
                    new_value = make_unicode(state).lower()
                        
        self.presenter.change_controller_setting(setting_name, new_value)

    def remove_controller(self, controller_id):
        pass # TODO
        
    def update_all_sensor_info(self, controller_id, sensor_id, sensor_info):        

        for key in sensor_info:        
            self.update_sensor_info(controller_id, sensor_id, key, sensor_info[key])   
         
    def update_sensor_info(self, controller_id, sensor_id, info_name, value):

        sensor_view = self.sensor_to_widget[(controller_id, sensor_id)]             
        sensor_view.update_sensor_view(info_name, value)

        if info_name == 'sensor_paused':
            self.update_sensor_list_widget(controller_id, sensor_id)  
        
    def remove_sensor(self, controller_id, sensor_id):
        #TODO create pop up window asking if they are sure they want to remove the sensor
        
        # switch to the controller view page 
        self.stacked_widget.setCurrentIndex(0)
        
        # remove sensor from appropriate dictionaries
        del self.sensor_to_widget[(controller_id, sensor_id)]
        del self.sensor_view_stack[(controller_id, sensor_id)]
        
        self.refresh_sensor_list_widget()
    
    def show_new_sensor_data(self, controller_id, sensor_id, data):
                
        # if the passed sensor is active, call function in sensor_viewer to update data visualization
        # data visualization
        if (controller_id, sensor_id) == (self.presenter.active_controller_id, self.presenter.active_sensor_id):
            
            sensor_view = self.sensor_to_widget[(controller_id, sensor_id)]
                        
            sensor_view.update_data_visualization(data)
            
    
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
        
    def refresh_current_issues(self, current_issues):
        
        # Remove all rows so we can re-add everything.
        self.current_issues_table.setRowCount(0)
        
        if len(current_issues) == 0:
            self.current_issues_table.setColumnCount(0)
            return # no issues to show in table
        
        self.issue_table_headers = ['Controller ID', 'Sub ID', 'Issue Type', 'Level', 'Reason', 'Acknowledged', 'Resolved', 'Duration']
        self.current_issues_table.setColumnCount(len(self.issue_table_headers))
        self.current_issues_table.setHorizontalHeaderLabels(self.issue_table_headers)
  
        for row_idx, issue in enumerate(current_issues):
            acked = 'Yes' if issue.acked else 'No'
            resolved = 'Yes' if issue.resolved else 'No'
            duration = issue.expiration_time - issue.start_time
            if duration < 0:
                duration = '' # issue doesn't have an end time yet.
            else:
                duration = '{:.2f}'.format(duration)
                
            table_values = [issue.id, issue.sub_id, pretty(issue.issue_type), pretty(issue.level),
                             issue.reason, acked, resolved, duration]
            
            self.current_issues_table.insertRow(row_idx)
            
            for column_idx, table_value in enumerate(table_values):
                
                table_item = QTableWidgetItem(table_value)
                table_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                
                self.current_issues_table.setItem(row_idx, column_idx, table_item)
                
                if issue.resolved:
                    table_item.setBackground(QtGui.QColor(194,248,255))
                
        self.current_issues_table.resizeColumnsToContents()
        #self.current_issues_table.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.current_issues_table.horizontalHeader().setStretchLastSection(True)
                
    def current_issue_clicked_on(self, row_idx, column_idx):
        
        self.presenter.acknowledge_issue_by_index(row_idx)
                
    def notify_new_issue(self, issue_info):
                
        self.new_issue_popup = NewIssuePopupWindow()
        #self.new_issue_popup.setModal(True)
        self.new_issue_popup.show()
                
    def logo_double_clicked(self, arg):
        
        if self.presenter.local_controller:
            session_path = self.presenter.local_controller['session_path']
            open_directory_in_viewer(session_path)

        