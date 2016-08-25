# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import yaml

# TODO clean up imports
from PyQt4.QtGui import *
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.Qt import Qt

from dysense.gui.sensor_view_widget_designer import Ui_sensor_view
from dysense.core.utility import pretty, make_unicode, format_decimal_places, limit_decimal_places

class SensorViewWidget(QWidget, Ui_sensor_view):
           
    def __init__(self, controller_id, sensor_info, presenter, view):
        #super().__init__()
        QWidget.__init__(self)
        self.setupUi(self) #call the auto-generated setupUi function in the designer file
        
        self.presenter = presenter
        self.view = view
        self.controller_id = controller_id
        self.sensor_info = sensor_info
        self.sensor_metadata = sensor_info['metadata']
        self.sensor_id = sensor_info['sensor_id']
        
        # Last state reported by driver.
        self.last_connection_state = 'unknown'
        
        #dictionaries for relating the sensor info names to their corresponding line edits/labels        
        self.info_name_to_object =  {
                               'sensor_type': self.sensor_type_line_edit,
                               'sensor_id': self.sensor_name_line_edit,                                      

                               'instrument_tag': self.sensor_id_line_edit,
                               'position_offsets': [self.forward_position_line_edit,
                                                    self.right_position_line_edit,
                                                    self.down_position_line_edit],
                               'orientation_offsets': [self.roll_orientation_line_edit,
                                                       self.pitch_orientation_line_edit,
                                                       self.yaw_orientation_line_edit],          
                               }
        
        # Populated when generating settings from metadata.
        self.setting_name_to_object = {}
        self.object_to_setting_name = {}
        
        # Populated when generating data line edits
        # key = index in data list from metadata
        # value = number of decimal places to display. False if not specified
        self.dec_places = {}
        
        # Populated when generating data visualization from metadata.       
        self.data_line_edits = []

        # get type dependent settings from metadata
        #default_settings = self.sensor_info['settings']
        sensor_type = sensor_info['sensor_type']
        self.setup_settings(self.sensor_info['settings'])
        
        # setup data visualization        
        self.setup_data_visualization()
        
        
        #set the special commands from metadata
        special_commands_list = self.sensor_metadata.get('special_commands', None)
        self.setup_special_commands(special_commands_list)
        
        #Set fields not to be edited by user as read only
        self.sensor_message_center_text_edit.setReadOnly(True)
        self.sensor_type_line_edit.setReadOnly(True)
        self.sensor_name_line_edit.setReadOnly(True)
        
        # Connect User Changes        
        self.sensor_id_line_edit.editingFinished.connect(self.instrument_id_changed)
        self.forward_position_line_edit.editingFinished.connect(self.position_offset_changed)
        self.right_position_line_edit.editingFinished.connect(self.position_offset_changed)
        self.down_position_line_edit.editingFinished.connect(self.position_offset_changed)
        self.roll_orientation_line_edit.editingFinished.connect(self.orientation_offset_changed)
        self.pitch_orientation_line_edit.editingFinished.connect(self.orientation_offset_changed)
        self.yaw_orientation_line_edit.editingFinished.connect(self.orientation_offset_changed)
                      
        #Connect main command buttons
        self.setup_sensor_button.clicked.connect(self.setup_sensor_button_clicked)
        self.start_sensor_button.clicked.connect(self.start_sensor_button_clicked)
        self.pause_sensor_button.clicked.connect(self.pause_sensor_button_clicked)
        self.close_sensor_button.clicked.connect(self.close_sensor_button_clicked)
        self.remove_sensor_button.clicked.connect(self.remove_sensor_button_clicked)
    
    def setup_settings(self, settings):
       
        self.settings_font = QtGui.QFont()
        self.settings_font.setPointSize(11)
        
        # Group Box (HLayout) -> Scroll Area -> Frame (Grid Layout)

        self.settings_frame = QtGui.QFrame()
        self.settings_frame_layout = QGridLayout()
        self.settings_frame.setLayout(self.settings_frame_layout)
        
        self.scroll_area = QtGui.QScrollArea()
        self.scroll_area.setWidget(self.settings_frame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        #self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        self.settings_group_box = QGroupBox()
        self.settings_group_box.setTitle('Settings')
        self.settings_group_box.setAlignment(QtCore.Qt.AlignHCenter)
        self.settings_group_box.setFont(self.settings_font)
        
        self.settings_group_box_layout = QtGui.QHBoxLayout()
        self.settings_group_box.setLayout(self.settings_group_box_layout)
        self.settings_group_box_layout.addWidget(self.scroll_area)
        
        self.top_horizontal_layout.addWidget(self.settings_group_box)
        
        box_size_policy = QtGui.QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        #box_size_policy.setHorizontalStretch(1)
        #box_size_policy.setVerticalStretch(1)
        self.settings_group_box.setSizePolicy(box_size_policy)
        
        self.settings_frame_layout.setMargin(1)
        self.settings_group_box_layout.setMargin(3)
        
        # create name labels, line edits, and units labels for settings
        for n, setting_metadata in enumerate(self.sensor_metadata['settings']):    
            
            name = setting_metadata.get('name', 'No name in metadata')
            default_value = setting_metadata.get('default_value', 'no default')
            units = setting_metadata.get('units', '')
            description = setting_metadata.get('description', '')
            
            self.name_label = QtGui.QLabel()
            self.units_label = QtGui.QLabel()
            self.line_edit = QtGui.QLineEdit()
            
            # Set tool tips
            self.name_label.setToolTip(description)
            self.units_label.setToolTip(description)
            self.line_edit.setToolTip(description)
            
            # Store the line edit references and corresponding name
            obj_ref = self.line_edit
            self.object_to_setting_name[obj_ref] = name
            self.setting_name_to_object[name] = obj_ref
            
            self.settings_frame_layout.addWidget(self.name_label, n, 0)
            self.settings_frame_layout.addWidget(self.line_edit, n, 1)
            self.settings_frame_layout.addWidget(self.units_label, n, 2)
            
            self.name_label.setText(pretty(name))   
            self.line_edit.setText(make_unicode(settings[name]))
            self.units_label.setText(pretty(units))
            
            # Connect the line edit signal
            self.line_edit.editingFinished.connect(self.setting_changed_by_user)

    def setup_data_visualization(self):
                
        self.data_group_box_layout = QtGui.QHBoxLayout()
        self.data_group_box.setLayout(self.data_group_box_layout)
        
        for n, data_metadata in enumerate(self.sensor_metadata['data']):
            
            name = data_metadata.get('name', 'No Name')
            units = data_metadata.get('units', False)
            decimal_places = data_metadata.get('decimal_places', False)  
             
            # Store number of decimal places if value is given
            self.dec_places[n] = decimal_places   
     
            self.name_label = QtGui.QLabel()
            self.name_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            self.name_label.setAlignment(Qt.AlignRight)
            self.line_edit = QtGui.QLineEdit()
            self.line_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.line_edit.setReadOnly(True)
            #Add units as tool tip
            if units:
                self.name_label.setToolTip(units)
                self.line_edit.setToolTip(units)
                
            # Store the line edit references and corresponding name
            self.data_line_edits.append(self.line_edit)            
            
            self.data_group_box_layout.addWidget(self.name_label)
            self.data_group_box_layout.addWidget(self.line_edit)
            
            self.name_label.setText(pretty(name) + ':')
             
    def setup_special_commands(self, special_commands):
        
        if special_commands == None:
            self.special_commands_group_box.deleteLater()
            return
        
        #special commands dict
        #key = reference
        #value = special command
        self.special_commands_references = {}
        
        special_commands_layout = QtGui.QHBoxLayout()
        self.special_commands_group_box.setLayout(special_commands_layout)
        for command in special_commands:
            
            b = QtGui.QPushButton(pretty(command))
            special_commands_layout.addWidget(b)
            
            # store the button object reference 
            obj_ref = make_unicode(b).split()[3]
            self.special_commands_references[obj_ref] = command  
            
            b.clicked.connect(self.special_command_clicked)
    
    def update_data_visualization(self, data):        
                 
        for n, line_edit in enumerate(self.data_line_edits):
            
            try:
                data_value = data[n]
            except IndexError:
                continue # not all data was provided
            
            if isinstance(data_value, float):
                     
                desired_decimal_places = self.dec_places[n]
                
                if desired_decimal_places == 0: # (number not specified)
                    data_value = limit_decimal_places(data_value, 5)
                else:
                    data_value = format_decimal_places(data_value, desired_decimal_places)

            line_edit.setText(make_unicode(data_value))
      
    def special_command_clicked(self):
                
        obj_ref = make_unicode(self.sender()).split()[3]    # TODO get rid of split, here and in setup_special_commands
        command = self.special_commands_references[obj_ref]
        
        # Set command arguments for special commands.
        command_args = None
        
        if command in ['save_primary', 'save_position']:
            user_notes, ok = QInputDialog.getText(self, 'Text Input Dialog', 'Notes:')
            if not ok:
                return # user cancelled so don't send command
            command_args = user_notes
        
        self.presenter.send_sensor_command(command, command_args)       
        
    def setting_changed_by_user(self):
        
        if not self.sender().isModified():
            return
        self.sender().setModified(False)
        
        new_value = self.sender().text()
        
        obj_ref = self.sender()  
        setting_name = self.object_to_setting_name[obj_ref]        
        
        self.presenter.change_sensor_setting(setting_name, new_value)
            
    #Update Viewer
    def update_sensor_view(self, info_name, value):       
          
        # Update all screen objects that correspond to the specified sensor info name. 
        matching_obj = self.info_name_to_object.get(info_name, [])
        if not isinstance(matching_obj, list):
            matching_obj.setText(make_unicode(value))
        else:
            for i, obj in enumerate(matching_obj):
                obj.setText(make_unicode(value[i]))
        
        if info_name == 'settings':
            settings = value
            for setting_name, setting_value in settings.iteritems():
                if setting_name in self.setting_name_to_object:
                    obj = self.setting_name_to_object[setting_name]
                    obj.setText(make_unicode(setting_value))
                   
        if info_name == 'overall_health':
            self.overall_sensor_health_update(value)                        
            
        if info_name == 'sensor_paused':
            if value == True:
                self.paused_label.setText('Paused')
            elif value == False:
                self.paused_label.setText('Active')
                
        if info_name == 'sensor_state':
            self.sensor_state_value_label.setText(pretty(value))
            
        if info_name == 'connection_state':
            current_connection_state = value
            if current_connection_state == 'setup' and self.last_connection_state != 'setup':
                self.sensor_message_center_text_edit.clear()
                for line_edit in self.data_line_edits:
                    line_edit.clear()
            self.last_connection_state = current_connection_state
            
#         if info_name == 'connection_state':
#             self.sensor_connection_state_label.setText(value)
        
    def instrument_id_changed(self):    
        
        if self.sender().isModified():
            new_value = self.sensor_id_line_edit.text()
            self.presenter.change_sensor_info('instrument_tag', new_value)
            self.sender().setModified(False)
             
    def position_offset_changed(self):    
        
        if self.sender().isModified():
            forward = self.forward_position_line_edit.text()
            right = self.right_position_line_edit.text()
            down = self.down_position_line_edit.text()
            self.presenter.change_sensor_info('position_offsets', [forward, right, down])
            self.sender().setModified(False)
     
    def orientation_offset_changed(self):    
        
        if self.sender().isModified():
            roll = self.roll_orientation_line_edit.text()
            pitch = self.pitch_orientation_line_edit.text()
            yaw = self.yaw_orientation_line_edit.text()
            self.presenter.change_sensor_info('orientation_offsets', [roll, pitch, yaw])
            self.sender().setModified(False)
    
    # clears and sets text messages for entire sensor update, appends messages for single message update    
    def display_message(self, message, append):
        
        if append == True:
            self.sensor_message_center_text_edit.append(make_unicode(message))
        else:
            self.sensor_message_center_text_edit.setText(make_unicode(message))

    def overall_sensor_health_update(self, health):

        if health in ['N/A', 'neutral']:
            self.sensor_health_value_label.setStyleSheet('color: black')  
            
        elif health == 'good':
            self.sensor_health_value_label.setStyleSheet('color: green')  
            
        elif health == 'bad':
            self.sensor_health_value_label.setStyleSheet('color: red')  
    
        self.sensor_health_value_label.setText(pretty(health))
        
    def clear_sensor_message_center_button_clicked(self):
        self.sensor_message_center_text_edit.clear() 
    
    
    #Main Commands
    def setup_sensor_button_clicked(self):
        self.presenter.setup_sensor()      
        
    def start_sensor_button_clicked(self):
        self.presenter.resume_sensor()
        
    def pause_sensor_button_clicked(self):
        self.presenter.pause_sensor() 
        
    def close_sensor_button_clicked(self):
        
        # TODO - update for multiple controllers - actually use controller that sensor is on.
        if self.presenter.local_controller['session_active']:
            question = "A session is active. Are you sure you want to close this sensor?"
            if not self.view.confirm_question(question):
                return
        
        self.presenter.close_sensor()         
            
    def remove_sensor_button_clicked(self):    
        
        question = "Are you sure you want to remove this sensor?"
        if not self.view.confirm_question(question):
            return
        
        self.presenter.remove_sensor(self.sensor_id)    

            
