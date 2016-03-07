
import time
import yaml
import sys
# Use default python types instead of QVariant
import sip
sip.setapi('QVariant', 2)

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QMetaObject, QObject, QEvent, Qt, Q_ARG
#from PyQt4.QtGui import QMainWindow, QColor, QWidget, QFileDialog
from PyQt4.QtGui import *
from dysense_main_window_designer import Ui_MainWindow
from sensor_view_widget import SensorViewWidget


class DysenseMainWindow(QMainWindow, Ui_MainWindow):
    
    def __init__(self, presenter):
        
        QMainWindow.__init__(self)
        
        self.presenter = presenter
        
        
        # Set up the user interface from Designer.
        self.setupUi(self)
        
        #set logo
        main_logo = QtGui.QPixmap('../resources/dysense_logo.png')
        main_logo = main_logo.scaled(90,80)      
        self.logo_label.setPixmap(main_logo)
        
        
                #example to create yaml file
#         new_sensor_info = {'version': '1.0',
#                                'sensor_type': 'test',
#                                'sensor_name': 'sensor1'}
#         stream = file('test_config.yaml', 'w')
#         yaml.dump(new_sensor_info, stream)
            
        
        #Lookup table of sensor views in the stacked widget
        #key - sensor id
        #value - index in stacked widget
        #menu page is always index 0 
        self.sensor_view_stack = {}
               
        
        #Lookup table of sensor 'items' in the list widget
        #key - tuple of (controller id, sensor id)
        #value - row position of list item
        self.sensor_list = {}

        #Set fields not to be edited by user as read only
        self.main_message_center_text_edit.setReadOnly(True)
        self.main_status_line_edit.setReadOnly(True)
        self.version_line_edit.setReadOnly(True)
        self.session_line_edit.setReadOnly(True)
        
        
        #Add sensor types to drop down box. For now, get them from a list of types - ask Kyle about this. Probably should have the types read in from metadata
        self.sensor_types = ['test_sensor_python', 'test_sensor_csharp', 'kinectv2_msdk', 'gps_nmea_test']
        self.sensor_type_combo_box.addItems(self.sensor_types)
            
                
        #Connect main command buttons
        self.menu_button.clicked.connect(self.menu_button_clicked)
        self.clear_main_message_center_button.clicked.connect(self.clear_main_message_center_button_clicked)
        
        #Connect sensor control buttons
        self.setup_sensors_button.clicked.connect(self.setup_sensors_button_clicked)
        self.start_sensors_button.clicked.connect(self.start_sensors_button_clicked)
        self.pause_sensors_button.clicked.connect(self.pause_sensors_button_clicked)
        self.resume_sensors_button.clicked.connect(self.resume_sensors_button_clicked)
        self.end_session_button.clicked.connect(self.end_session_button_clicked)
        self.close_sensors_button.clicked.connect(self.close_sensors_button_clicked)
        
        
             
        #TODO: Add save config functionality
        #self.save_config_button.clicked.connect(self.save_config_button_clicked)
        
        #Config buttons
        self.select_config_tool_button.clicked.connect(self.select_config_tool_button_clicked)
        self.load_config_button.clicked.connect(self.load_config_button_clicked)
        
        self.add_sensor_button.clicked.connect(self.add_sensor_button_clicked)
        
        self.sensor_list_widget.itemClicked.connect(self.list_item_clicked)
                
      
    #TODO: Add the main actions functionality after getting Kyle's updates   
    def setup_sensors_button_clicked(self):
        self.presenter.setup_all_sensors(True)
        pass
    def start_sensors_button_clicked(self):
        pass #may need to add method in presenter
    
    def pause_sensors_button_clicked(self):
        #self.presenter.pause_all_sensors(True)
        pass
    
    def resume_sensors_button_clicked(self):
        #self.presenter.resume_all_sensors(True)
        pass             
                               
    def end_session_button_clicked(self):
        pass #method will be added to presenter by Kyle
    
    def close_sensors_button_clicked(self):
        #self.presenter.close_all_sensors(True)
        print self.sensor_list
        print self.sensor_list_widget.count()



    def create_new_sensor_view(self, controller_id, sensor_id, sensor_info):
        
        new_sensor_view = SensorViewWidget(controller_id, sensor_info, self.presenter)
        
        #Add the sensor view widget to the stack
        self.stacked_widget.addWidget(new_sensor_view)
            
        #Add the widget to sensor_view_stack dict - currently used in show_sensor
        self.sensor_view_stack[sensor_id] = self.stacked_widget.indexOf(new_sensor_view)
        
        stack_index = self.stacked_widget.indexOf(new_sensor_view)
        
        #add widget instance and index to the sensor_info
        sensor_info['widget'] = new_sensor_view
        sensor_info['widget_index'] = stack_index
                
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
        
    def update_sensor_list_widget(self, controller_id, sensor_id, new_name):
        row = self.sensor_list[(controller_id, sensor_id)]
        item = self.sensor_list_widget.item(row)
        item.setText(new_name)
        
        
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
        print 'menu btn clicked'
        
    def clear_main_message_center_button_clicked(self):
        self.main_message_center_text_edit.clear()
    
    def select_config_tool_button_clicked(self):
        #hard coded for testing
        self.config_line_edit.setText('C:/Users/ejwel_000/Workspaces/DySense/DySense/source/test_config.yaml')
        
        #correct way
        #self.config_line_edit.setText(QFileDialog.getOpenFileName())
        
    def load_config_button_clicked(self):
        path = self.config_line_edit.text()
        
        stream = file(path, 'r')
        
        sensor_info = yaml.load(stream)
        
        self.add_sensor_button_clicked(sensor_info)
         
#       TODO  
#     def save_config_button_clicked(self):
#         #use data from current configuration and write it to a YAML file

             
    def display_message(self, message):
        self.main_message_center_text_edit.append(message)
        
    def update_all_controller_info(self, controller_id, controller_info):
        self.presenter.controllers[controller_id] = controller_info
        self.display_message("Controller: ({}) received with info\n{}".format(controller_id, controller_info))
        
    def remove_controller(self, controller_id):
        self.display_message("Controller: ({}) removed".format(controller_id))
        
    def update_all_sensor_info(self, controller_id, sensor_id, sensor_info):
        
        sensor_view = sensor_info['widget']
        
        #loop through key and value pairs and call update_sensor_info for each one
        for key in sensor_info:
            #print key, ' == ', sensor_info[key]
            
            self.update_sensor_info(controller_id, sensor_id, key, sensor_info[key])   
              
        self.display_message("Sensor: ({}:{}) received with info\n{}".format(controller_id, sensor_info['sensor_name'],
                                                                            str(sensor_info).replace(',', ',\n')))
         
    def update_sensor_info(self, controller_id, sensor_id, info_name, value):
        
        sensor_info = self.presenter.sensors[(controller_id,sensor_id)]
        sensor_view = sensor_info['widget']                
        sensor_view.update_sensor_view(info_name, value)
        self.display_message("Sensor ({}:{}) had \'{}\' changed to {}".format(controller_id, sensor_id, info_name, value))
        
    def remove_sensor(self, controller_id, sensor_id):
        self.display_message("Sensor ({}:{}) removed".format(controller_id, sensor_id))
    
    def show_new_sensor_data(self, controller_id, sensor_id, data):
        self.display_message("Sensor ({}:{}) new data {}".format(controller_id, sensor_id, data))
    
    def append_sensor_message(self, controller_id, sensor_id, text):
        self.display_message("Sensor ({}:{}) new text {}".format(controller_id, sensor_id, text))   
        