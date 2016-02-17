
import time

# Use default python types instead of QVariant
import sip
sip.setapi('QVariant', 2)

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QMetaObject, QObject, QEvent, Qt, Q_ARG
from PyQt4.QtGui import QMainWindow, QColor, QWidget

class TestWindow(QWidget):
    
    def __init__(self, presenter):
        
        QWidget.__init__(self)
        
        self.presenter = presenter
        
        # Lookup table of controller information.
        # key - controller id 
        # value - dictionary of controller info.
        self.controllers = {}
        
        # Lookup table of sensor information.
        # key - tuple of (controller id, sensor id)
        # value - dictionary of sensor info.
        self.sensors = {}
    
        # For keeping track of number of button presses.
        self.test_step = 0
        
        self.start_button = QtGui.QPushButton("Add Test Sensor")

        self.message_center_text_edit = QtGui.QTextEdit()
        self.message_center_text_edit.setMinimumSize(QtCore.QSize(1000, 0))
        self.message_center_text_edit.setReadOnly(True)
        
        self.vbox = QtGui.QVBoxLayout()
        self.vbox.addWidget(self.start_button)
        self.vbox.addWidget(self.message_center_text_edit)
        
        self.setLayout(self.vbox)
        
        self.start_button.clicked.connect(self.start_button_clicked)
        
    def start_button_clicked(self):
        
        # Should already have one controller (the local one on this computer).
        # The main API to the presenter is you set an active controller (and active sensor) and then most
        # of the methods you call are directed towards whatever's active.  So it's critical you keep those
        # 'active ids' in the presenter in-sync with what's on the screen.
        # Normally this 'setting active' would happen from user clicking on the controller in the tree view.
        self.presenter.active_controller_id = self.controllers.keys()[0]
        
        if self.test_step == 0:
            self.display_message("Telling presenter to add new sensor...")
            #new_sensor_info = {'version': '1.0',
            #                   'sensor_type': 'kinectv2_msdk',
            #                   'sensor_name': 'kinectv2_1'}

            # Add test sensor
            new_sensor_info = {'version': '1.0',
                               'sensor_type': 'test_sensor_python',
                               'sensor_name': 'test_sensor'}
            self.presenter.add_sensor(new_sensor_info)
            
            self.start_button.setText('Setup Sensor')
            
        if self.test_step == 1:
            
            self.display_message("Telling presenter to setup active sensor...")
            self.presenter.setup_sensor()
            #self.presenter.setup_all_sensors(True)
            self.start_button.setText('Start Sensor')
            
        if self.test_step == 2:
            
            self.display_message("Telling presenter to start active sensor...")
            self.presenter.resume_sensor()
            #self.presenter.resume_all_sensors(True)
            self.start_button.setText('Add GPS')
            
        if self.test_step == 3:
            self.display_message("Telling presenter to add gps...")
            # Add test GPS source
            new_gps_info = {'version': '1.0',
                               'sensor_type': 'gps_nmea_test',
                               'sensor_name': 'gps'}
            new_gps_info['settings'] = {'test_file_path': r"C:\Users\Kyle\Documents\DySense\nmea_logs\SXBlueGGA.txt",
                                           'output_rate': 10,
                                           'required_fix': 'none',
                                           'required_precision': 0}
            self.presenter.add_sensor(new_gps_info)
            
            self.start_button.setText('Setup GPS')
        
        if self.test_step == 4:
            
            self.display_message("Telling presenter to set sensor 2 as time source..")
            new_time_source = {"controller_id": self.presenter.active_controller_id, "sensor_id": '2'}
            self.presenter.change_controller_data_source('time', new_time_source)
            
            self.display_message("Telling presenter to setup GPS...")
            self.presenter.setup_sensor()
            
            self.start_button.setText('Start GPS')
        
        if self.test_step == 5:
            self.display_message("Telling presenter to start GPS...")
            self.presenter.resume_sensor()
            
            self.start_button.setText('Pause Test Sensor')
            self.presenter.active_sensor_id = '1'
            
        if self.test_step == 6:
            
            self.display_message("Telling presenter to pause active sensor...")
            self.presenter.pause_sensor()
            #self.presenter.pause_all_sensors(True)
            self.start_button.setText('Close Sensors')
            
        if self.test_step == 7:
            
            self.display_message("Telling presenter to close all sensors...")
            self.presenter.close_all_sensors(True)
            self.start_button.setText('Remove Sensors')
            
        if self.test_step == 8:
            
            self.display_message("Telling presenter to remove all sensors...")
            self.presenter.remove_all_sensors(True);
            self.start_button.setText('Done')
        
        self.test_step += 1
        
    def display_message(self, message):
        self.message_center_text_edit.append(message)
        
    def update_all_controller_info(self, controller_id, controller_info):
        self.controllers[controller_id] = controller_info
        self.display_message("Controller: {} updated info".format(controller_id))
        
    def remove_controller(self, controller_id):
        self.display_message("Controller: {} removed".format(controller_id))
        
    def update_all_sensor_info(self, controller_id, sensor_id, sensor_info):
        sensor_info['posted_about_receiving_data'] = False
        self.sensors[(controller_id, sensor_id)] = sensor_info
        self.display_message("Sensor: {} received".format(sensor_info['sensor_name']))
        self.presenter.active_sensor_id = sensor_id
    
    def update_sensor_info(self, controller_id, sensor_id, info_name, value):
        self.display_message("Sensor {} had \'{}\' changed to {}".format(self.sensors[(controller_id, sensor_id)]['sensor_name'],
                                                                        info_name, value))
        #self.display_message("Sensor ({}:{}) had \'{}\' changed to {}".format(controller_id, sensor_id, info_name, value))
    
    def remove_sensor(self, controller_id, sensor_id):
        self.display_message("Sensor {} removed".format(sensor_id))
    
    def show_new_sensor_data(self, controller_id, sensor_id, data):
        
        if not self.sensors[(controller_id, sensor_id)]['posted_about_receiving_data']:
            self.display_message("Sensor {} new data {}".format(sensor_id, data))
            self.sensors[(controller_id, sensor_id)]['posted_about_receiving_data'] = True
    
    def append_sensor_message(self, controller_id, sensor_id, text):
        self.display_message("Sensor {} new text {}".format(sensor_id, text)) 
