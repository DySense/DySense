# Use default python types instead of QVariant
import sip
sip.setapi('QVariant', 2)

from PyQt4.QtGui import *
from sensor_view_widget_designer import Ui_Form
from PyQt4 import QtGui
from decimal import *
import yaml
from utility import pretty



class SensorViewWidget(QWidget,Ui_Form):
           
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

                               'instrument_id': self.sensor_id_line_edit,
                               'position_offsets': [self.forward_position_line_edit,
                                                    self.left_position_line_edit,
                                                    self.up_position_line_edit],
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
        
                                        #'output_rate': self.capture_rate_line_edit                                                                           
                                        
        
        
        
#         
#          new_gps_info['settings'] = {'test_file_path': "..nmea_logs\SXBlueGGA.txt",
#                                            'output_rate': 1,
#                                            'required_fix': 'none',
#                                            'required_precision': 0}
#         
       
        

        
        
        
        # get type dependent settings from metadata
        #default_settings = self.sensor_info['settings']
        sensor_type = sensor_info['sensor_type']
        self.setup_settings(self.sensor_info['settings'])
        
        # setup data visualization        
        self.setup_data_visualization()
        
        
        #set the special commands from metadata
        special_commands_list = self.sensor_metadata.get('special_commands', None)
        self.setup_special_commands(special_commands_list)
        
        
        #setup health icons #TODO crop whitespace from edges of icons and figure out why good_icon pixmap is null
        self.neutral_icon = QtGui.QPixmap('../resources/grey_neutral_icon.png')
        self.neutral_icon = self.neutral_icon.scaled(65,63)      
        self.good_icon = QtGui.QPixmap('../resources/green_check_icon.jpg')
        #self.good_icon = QtGui.QPixmap('../resources/grey_neutral_icon.png')
        self.good_icon = self.good_icon.scaled(65,63)
        self.bad_icon = QtGui.QPixmap('../resources/red_x_icon.png')
        self.bad_icon = self.bad_icon.scaled(65,63)
        
        
        #Set fields not to be edited by user as read only
        self.sensor_message_center_text_edit.setReadOnly(True)
        self.sensor_type_line_edit.setReadOnly(True)
        self.sensor_name_line_edit.setReadOnly(True)
           
        
        # Connect User Changes        
        self.sensor_id_line_edit.editingFinished.connect(self.instrument_id_changed)
        self.forward_position_line_edit.editingFinished.connect(self.position_offset_changed)
        self.left_position_line_edit.editingFinished.connect(self.position_offset_changed)
        self.up_position_line_edit.editingFinished.connect(self.position_offset_changed)
        self.roll_orientation_line_edit.editingFinished.connect(self.orientation_offset_changed)
        self.pitch_orientation_line_edit.editingFinished.connect(self.orientation_offset_changed)
        self.yaw_orientation_line_edit.editingFinished.connect(self.orientation_offset_changed)
                      
        #Connect main command buttons
        self.setup_sensor_button.clicked.connect(self.setup_sensor_button_clicked)
        self.start_sensor_button.clicked.connect(self.start_sensor_button_clicked)
        self.pause_sensor_button.clicked.connect(self.pause_sensor_button_clicked)
        self.close_sensor_button.clicked.connect(self.close_sensor_button_clicked)
        self.remove_sensor_button.clicked.connect(self.remove_sensor_button_clicked)
        
        #Connect clear button
        #self.clear_sensor_message_center_button.clicked.connect(self.clear_sensor_message_center_button_clicked)
    

    def setup_settings(self, settings):
       
        self.settings_group_box_layout = QtGui.QGridLayout()
        self.settings_group_box.setLayout(self.settings_group_box_layout)
        
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
            
            self.settings_group_box_layout.addWidget(self.name_label, n, 0)
            self.settings_group_box_layout.addWidget(self.line_edit, n, 1)
            self.settings_group_box_layout.addWidget(self.units_label, n, 2)
            
            self.name_label.setText(pretty(name))   
            self.line_edit.setText(str(settings[name]))
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
            self.line_edit = QtGui.QLineEdit()
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
            obj_ref = str(b).split()[3]
            self.special_commands_references[obj_ref] = command  
            
            b.clicked.connect(self.special_command_clicked)
    
    def update_data_visualization(self, data):        
                 

        for n, line_edit in enumerate(self.data_line_edits):
            try:
                if isinstance(data[n], float):
                         
                    desired_length = self.dec_places[n] # = False if not specified
                    
                    current_length = abs(Decimal(str(data[n])).as_tuple().exponent)
                    
                    if desired_length: # set number of decimal places to desired length if given
                        line_edit.setText(str('{:.{prec}f}'.format(data[n], prec=desired_length)))
                        
                    elif current_length > 5: # if float has more than 5 dec places, cap it at 5
                        line_edit.setText(str("{0:.5f}".format(data[n])))           
                        
                    else:
                        line_edit.setText(str(data[n]))       
                                        
                else:
                    line_edit.setText(str(data[n]))
                        
                        
            except IndexError:
                pass # not all data was provided
                  
    def special_command_clicked(self):
                
        obj_ref = str(self.sender()).split()[3]    # TODO get rid of split, here and in setup_special_commands
        command = self.special_commands_references[obj_ref]
        
        self.presenter.send_sensor_command(command)       
        
    def setting_changed_by_user(self):
        
        if not self.sender().isModified():
            return
        self.sender().setModified(False)
        
        new_value = str(self.sender().text())
        
        obj_ref = self.sender()  
        setting_name = self.object_to_setting_name[obj_ref]        
        
        self.presenter.change_sensor_setting(setting_name, new_value)
            
    #Update Viewer
    def update_sensor_view(self, info_name, value):       
          
        # Update all screen objects that correspond to the specified sensor info name. 
        matching_obj = self.info_name_to_object.get(info_name, [])
        if not isinstance(matching_obj, list):
            matching_obj.setText(str(value))
        else:
            for i, obj in enumerate(matching_obj):
                obj.setText(str(value[i]))
        
        if info_name == 'settings':
            settings = value
            for setting_name, setting_value in settings.iteritems():
                if setting_name in self.setting_name_to_object:
                    obj = self.setting_name_to_object[setting_name]
                    obj.setText(str(setting_value))
                   
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
            self.last_connection_state = current_connection_state
            
#         if info_name == 'connection_state':
#             self.sensor_connection_state_label.setText(value)
        
    def instrument_id_changed(self):    
        
        if self.sender().isModified():
            new_value = str(self.sensor_id_line_edit.text())
            self.presenter.change_sensor_info('instrument_id', new_value)
            self.sender().setModified(False)
             
    def position_offset_changed(self):    
        
        if self.sender().isModified():
            forward = str(self.forward_position_line_edit.text())
            left = str(self.left_position_line_edit.text())
            up = str(self.up_position_line_edit.text())
            self.presenter.change_sensor_info('position_offsets', [forward, left, up])
            self.sender().setModified(False)
     
    def orientation_offset_changed(self):    
        
        if self.sender().isModified():
            roll = str(self.roll_orientation_line_edit.text())
            pitch = str(self.pitch_orientation_line_edit.text())
            yaw = str(self.yaw_orientation_line_edit.text())
            self.presenter.change_sensor_info('orientation_offsets', [roll, pitch, yaw])
            self.sender().setModified(False)
    
    # clears and sets text messages for entire sensor update, appends messages for single message update    
    def display_message(self, message, append):
        
        if append == True:
            self.sensor_message_center_text_edit.append(message)
        else:
            self.sensor_message_center_text_edit.setText(message)
         

    
    def overall_sensor_health_update(self, health):
        # call method to update change list widget item color for corresponding health
        self.view.update_list_widget_color(self.controller_id, self.sensor_id, health)
        
        if health in ['N/A', 'neutral']:
            self.sensor_health_icon_label.setPixmap(self.neutral_icon)    
            
        elif health == 'good':
            self.sensor_health_icon_label.setPixmap(self.good_icon)
            
        elif health == 'bad':
            self.sensor_health_icon_label.setPixmap(self.bad_icon)
    
        
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
        self.presenter.close_sensor()         
            
    def remove_sensor_button_clicked(self):    
        self.presenter.remove_sensor(self.sensor_id)    

            
