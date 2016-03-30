
import time
import yaml
import sys
import logging
import os
# Use default python types instead of QVariant
import sip
sip.setapi('QVariant', 2)

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QMetaObject, QObject, QEvent, Qt, Q_ARG
#from PyQt4.QtGui import QMainWindow, QColor, QWidget, QFileDialog
from PyQt4.QtGui import *
from dysense_main_window_designer import Ui_MainWindow
from sensor_view_widget import SensorViewWidget
from utility import pretty

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
#         main_logo = QtGui.QPixmap('../resources/dysense_logo_no_text.png')
#         main_logo = main_logo.scaled(90,80)      
#         self.logo_label.setPixmap(main_logo)
        
        #set version number
        # TODO the version from metadata should be the 'controller' version once
        # we support multiple of those and the GUI version should come from ui_settings.py
        version = self.sensor_metadata.get('version', 'No Version Number')
        self.version_value_label.setText(version)
             
        
                #example to create yaml file
#         new_sensor_info = {'version': '1.0',
#                                'sensor_type': 'test',
#                                'sensor_name': 'sensor1'}
#         stream = file('test_config.yaml', 'w')
#         yaml.dump(new_sensor_info, stream)
            
        
        # Associate sensor (controller_id, sensor_id) to its widget.
        self.sensor_to_widget = {}
            
            
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
                                        'platform_name': self.platform_name_line_edit,
                                        'platform_id': self.platform_id_line_edit,
                                        'field_id': self.field_id_line_edit,
                                        'surveyed': self.surveyed_check_box                                     
                                        }   
            

        
        #Lookup table of sensor views in the stacked widget
        #key - sensor id
        #value - index in stacked widget
        #menu page is always index 0 
        self.sensor_view_stack = {}
               
        
        #Lookup table of sensor 'items' in the list widget
        #key - tuple of (controller id, sensor id)
        #value - row position of list item
        self.sensor_list = {}
        
        # Connect controller setting line edits
        self.output_directory_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.operator_name_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.platform_name_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.platform_id_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.field_id_line_edit.editingFinished.connect(self.controller_setting_changed_by_user)
        self.surveyed_check_box.clicked.connect(self.controller_setting_changed_by_user)
        
        # Connect output directory file dialog button
        self.output_directory_tool_button.clicked.connect(self.output_directory_tool_button_clicked)
        
        #Set fields not to be edited by user as read only
        self.main_message_center_text_edit.setReadOnly(True)
        
                
        #Connect main command buttons
        self.menu_button.clicked.connect(self.menu_button_clicked)
        self.clear_main_message_center_button.clicked.connect(self.clear_main_message_center_button_clicked)
        
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
        
        self.sensor_list_widget.itemClicked.connect(self.list_item_clicked)
        
        # Populate last saved config file so user doesn't always have to select it.
        self.config_line_edit.setText(self.last_loaded_config_file_path)
        
              
                
    @property
    def last_saved_config_file_path(self):
        file_path = self.qt_settings.value("last_saved_config_file_path")
        if file_path is None:
            file_path = os.path.join(os.path.expanduser('~'), 'dysense_config.yaml')
        return str(file_path)
        
    @last_saved_config_file_path.setter
    def last_saved_config_file_path(self, new_value):
        self.qt_settings.setValue("last_saved_config_file_path", new_value)
      
    @property
    def last_loaded_config_file_path(self):
        file_path = self.qt_settings.value("last_loaded_config_file_path")
        return str(file_path)
        
    @last_loaded_config_file_path.setter
    def last_loaded_config_file_path(self, new_value):
        self.qt_settings.setValue("last_loaded_config_file_path", new_value)
      
    def set_possible_sensor_types(self, possible_sensor_types):
        self.sensor_type_combo_box.clear()
        self.sensor_type_combo_box.addItems(possible_sensor_types)
      
      
    def setup_sensors_button_clicked(self):
        self.presenter.setup_all_sensors(only_on_active_controller=True)
        
    def start_session_button_clicked(self):
        self.presenter.send_controller_command('start_session', send_to_all_controllers=False) 
    
    def pause_sensors_button_clicked(self):
        self.presenter.pause_all_sensors(only_on_active_controller=True)
            
    def resume_sensors_button_clicked(self):
        self.presenter.resume_all_sensors(only_on_active_controller=True)                     
                               
    def end_session_button_clicked(self):
        self.presenter.send_controller_command('stop_session', send_to_all_controllers=False)
    
    def close_sensors_button_clicked(self):
        
        self.presenter.close_all_sensors(only_on_active_controller=True)
    
    def update_list_widget_color(self, controller_id, sensor_id, health):
        if (controller_id, sensor_id) in self.sensor_list:
            row = self.sensor_list[(controller_id, sensor_id)]
            item = self.sensor_list_widget.item(row)
            
            if health in ['N/A', 'neutral']:                      
                item.setBackgroundColor(QColor(255,255,255)) #white
                                        
            elif health == 'good':
                item.setBackgroundColor(QColor(12,245,0)) # light green
                  
            elif health == 'bad':
                item.setBackgroundColor(QColor(250,145,145)) # light red
    
    def create_new_sensor_view(self, controller_id, sensor_id, sensor_info):
        
        new_sensor_view = SensorViewWidget(controller_id, sensor_info, self.presenter, self)
        
        #Add the sensor view widget to the stack
        self.stacked_widget.addWidget(new_sensor_view)
            
        #Add the widget to sensor_view_stack dict - currently used in show_sensor
        self.sensor_view_stack[sensor_id] = self.stacked_widget.indexOf(new_sensor_view)
        
        stack_index = self.stacked_widget.indexOf(new_sensor_view)
        
        #add widget instance and index to the sensor_info
        self.sensor_to_widget[(controller_id, sensor_id)] = new_sensor_view
                
        self.update_all_sensor_info(controller_id, sensor_id, sensor_info)
            
    def add_sensor_button_clicked(self, sensor_info):
        
        #Get sensor type from the sensor type drop down
        new_sensor_info =  {'sensor_type': str(self.sensor_type_combo_box.currentText()), 
                            'sensor_name': 'new_sensor_name'}
        
        self.presenter.add_sensor(new_sensor_info)              
        
    def add_sensor_to_list_widget(self, controller_id, sensor_id, sensor_name):
        
        
        row = self.sensor_list_widget.count()
        
        #Add sensor to sensor_list dict to keep track of items in list
        self.sensor_list[(controller_id, sensor_id)] = row
            
        
        self.sensor_list_widget.addItem(sensor_name)
        
    def update_sensor_list_widget(self, controller_id, sensor_id):
        
        sensor = self.presenter.sensors[(controller_id, sensor_id)]
        sensor_name = sensor['sensor_name']
        if sensor['sensor_paused']:
            sensor_name += ' (paused)'
        
        row = self.sensor_list[(controller_id, sensor_id)]
        item = self.sensor_list_widget.item(row)
        item.setText(sensor_name)
        
    def list_item_clicked(self, item):
                
        #item name = text of item in display list, which is the same as the sensor name
        row = self.sensor_list_widget.currentRow()
        
        #get the tuple of ids based on the name of the item clicked  
        for key in self.sensor_list:
            if self.sensor_list[key] == row:
                ids = key
                
        controller_id = ids[0]
        sensor_id = ids[1] 
                
        self.presenter.new_sensor_selected(controller_id, sensor_id)     
            
      
    def show_sensor(self,sensor_id):
        self.stacked_widget.setCurrentIndex(self.sensor_view_stack[sensor_id])
        
        #TODO - call self.presenter.update_active_sensor to update both the controller and sensor ids
        #for now, just update the sensor here and assume one controller
        self.presenter.active_sensor_id = sensor_id

                
    def menu_button_clicked(self):
        #set menu page to the front of the stacked widget, menu page will always be index 0
        self.stacked_widget.setCurrentIndex(0)
        
        # deselect list widget items so health color shows   
        for i in range(self.sensor_list_widget.count()):
            item = self.sensor_list_widget.item(i)
            self.sensor_list_widget.setItemSelected(item, False)
        
    def clear_main_message_center_button_clicked(self):
        self.main_message_center_text_edit.clear()
    
    
    def output_directory_tool_button_clicked(self):
        output_directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.output_directory_line_edit.setText(output_directory)
        self.output_directory_line_edit.setModified(True)
        self.output_directory_line_edit.editingFinished.emit()
        
    def select_config_tool_button_clicked(self):
        
        config_file_path = QtGui.QFileDialog.getOpenFileName(self, 'Load Config', self.last_loaded_config_file_path,
                                                             selectedFilter='*.yaml')

        if not config_file_path:
            return # User didn't select a config file.

        self.last_loaded_config_file_path = config_file_path

        self.config_line_edit.setText(config_file_path)
        
    def load_config_button_clicked(self):

        config_file_path = self.config_line_edit.text()
        
        self.presenter.load_config(config_file_path)
 
    def save_config_button_clicked(self):

        config_file_path = QtGui.QFileDialog.getSaveFileName(self, 'Save Config', self.last_saved_config_file_path,
                                                      selectedFilter='*.yaml')

        if not config_file_path:
            return # User doesn't want to save the file.
        
        self.last_saved_config_file_path = config_file_path
        
        self.presenter.save_config(config_file_path)
             
    def display_message(self, message):
        self.main_message_center_text_edit.append(message)
        
    def update_all_controller_info(self, controller_id, controller_info):
        self.controller_info = controller_info # TESTING
        self.presenter.controllers[controller_id] = controller_info

        for info_name, value in controller_info.iteritems():
            
            if info_name in self.name_to_object:
                obj = self.name_to_object[info_name]
                obj.setText(value)
                
            if info_name == 'session_active':
                self.session_value_label.setText(str('Active' if value else 'Not Started'))
                
            if info_name == 'session_state':
                self.main_status_value_label.setText(pretty(value))
            
            if info_name == 'settings':
                settings = value 
                for settings_name, settings_value in settings.iteritems():               
                                    
                    if settings_name == 'surveyed':
                        if str(settings_value).lower() == 'true':
                            self.surveyed_check_box.setChecked(True)
                        else:
                            self.surveyed_check_box.setChecked(False)
                        continue              
                    
                    if settings_name in self.settings_name_to_object:
                        obj = self.settings_name_to_object[settings_name]
                        obj.setText(str(settings_value))
            
    def controller_setting_changed_by_user(self):
        obj_ref = self.sender()  
        
        if isinstance(obj_ref, QLineEdit) and not obj_ref.isModified():
            return
        
        #the new value will be the text in the line edits, except when it is the surveyed checkbox. 
        new_value = str(self.sender().text())        
        
        for key in self.settings_name_to_object:
            if self.settings_name_to_object[key] == obj_ref:  
                setting_name = key
                
                                
                if setting_name == 'surveyed':
                    state = self.surveyed_check_box.isChecked()
                    new_value = str(state).lower()
                    
                
                        
        self.presenter.change_controller_setting(setting_name, new_value)
         
                     
   
    def remove_controller(self, controller_id):
        pass # TODO
        
    def update_all_sensor_info(self, controller_id, sensor_id, sensor_info):        
        # TODO handle messages that should be appended vs clearing message center and set.
        # clear sensor message center and set new text messages when all sensor info is updated
        #  messages = sensor_info.get('text_messages', '')        
#         sensor_view = sensor_info['widget']
#         sensor_view.display_message(str(messages).strip('[]').replace(',', ',\n'), False)
                
        #loop through key and value pairs and call update_sensor_info for each one
        for key in sensor_info:        
            self.update_sensor_info(controller_id, sensor_id, key, sensor_info[key])   
         
    def update_sensor_info(self, controller_id, sensor_id, info_name, value):

        sensor_view = self.sensor_to_widget[(controller_id, sensor_id)]             
        sensor_view.update_sensor_view(info_name, value)

        if info_name == 'sensor_name' or info_name == 'sensor_paused':
            self.update_sensor_list_widget(controller_id, sensor_id)  
        
    def remove_sensor(self, controller_id, sensor_id):
        #TODO create pop up window asking if they are sure they want to remove the sensor
        
        # switch to the controller view page 
        self.stacked_widget.setCurrentIndex(0)
        
        # remove sensor item from list widget
        row_to_delete = self.sensor_list[(controller_id, sensor_id)]
        self.sensor_list_widget.takeItem(row_to_delete)
        
        # shift affected rows down by one to stay in sync with list widget
        for key in self.sensor_list:
            if self.sensor_list[key] > row_to_delete:
                self.sensor_list[key] -= 1
                
        # remove sensor from appropriate dictionaries
        del self.sensor_view_stack[sensor_id]
        del self.sensor_list[(controller_id, sensor_id)]
    
    def show_new_sensor_data(self, controller_id, sensor_id, data):
                
        # if the passed sensor is active, call function in sensor_viewer to update data visualization
        # data visualization
        if (controller_id, sensor_id) == (self.presenter.active_controller_id, self.presenter.active_sensor_id):
            
            sensor_view = self.sensor_to_widget[(controller_id, sensor_id)]
                        
            sensor_view.update_data_visualization(data)
            
    
    def append_sensor_message(self, controller_id, sensor_id, text):

        sensor_view = self.sensor_to_widget[(controller_id, sensor_id)]  
        sensor_view.display_message(str(text).strip('[]').replace(',', ',\n'), True)  
        
    def show_error_message(self, message, level):
        
        popup = QtGui.QMessageBox()
        
        if level == logging.CRITICAL:
            level_text = "Critical Error"
            icon = QStyle.SP_MessageBoxCritical
        elif level == logging.ERROR:
            level_text = "Error"
            icon = QStyle.SP_MessageBoxWarning
        else:
            return # not a level we need to show
            
        popup.setText(message)
        popup.setWindowTitle('{}!'.format(level_text))
        popup.setWindowIcon(popup.style().standardIcon(icon))
        
        popup.exec_()

        