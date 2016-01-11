
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
        
        self.controllers = {}
        self.sensors = {}
        
        self.test_step = 0
        
        self.start_button = QtGui.QPushButton("Add Sensor")

        self.message_center_text_edit = QtGui.QTextEdit()
        self.message_center_text_edit.setMinimumSize(QtCore.QSize(1000, 0))
        self.message_center_text_edit.setReadOnly(True)
        
        self.vbox = QtGui.QVBoxLayout()
        self.vbox.addWidget(self.start_button)
        self.vbox.addWidget(self.message_center_text_edit)
        
        self.setLayout(self.vbox)
        
        self.start_button.clicked.connect(self.start_button_clicked)
        
    def start_button_clicked(self):
        
        self.presenter.active_controller_id = self.controllers.keys()[0]
        
        if self.test_step == 0:
            self.display_message("Telling presenter to add new sensor...")
            new_sensor_info = {'version': '1.0',
                               'sensor_type': 'test',
                               'sensor_name': 'sensor1'}
            self.presenter.add_sensor(new_sensor_info)
            self.start_button.setText('Change Sensor Name')
            
        if self.test_step == 1:
            if len(self.sensors) == 0:
                return
            self.presenter.active_sensor_id = self.sensors.keys()[0][1]
            
            self.display_message("Telling presenter to change sensor name to test_sensor1...")
            self.presenter.change_sensor_info('sensor_name', 'test_sensor1')
            self.start_button.setText('Setup Sensor')
            
        if self.test_step == 2:
            
            self.display_message("Telling presenter to setup active sensor...")
            self.presenter.setup_sensor()
            #self.presenter.setup_all_sensors(True)
            self.start_button.setText('Start Sensor')
            
        if self.test_step == 3:
            
            self.display_message("Telling presenter to start active sensor...")
            self.presenter.resume_sensor()
            #self.presenter.resume_all_sensors(True)
            self.start_button.setText('Pause Sensor')
            
        if self.test_step == 4:
            
            self.display_message("Telling presenter to pause active sensor...")
            self.presenter.pause_sensor()
            #self.presenter.pause_all_sensors(True)
            self.start_button.setText('Remove Sensor')
            
        if self.test_step == 5:
            
            self.display_message("Telling presenter to remove active sensor...")
            self.presenter.remove_sensor(self.presenter.active_sensor_id)
            self.start_button.setText('Done')
        
        self.test_step += 1
        
    def display_message(self, message):
        self.message_center_text_edit.append(message)
        
    def update_all_controller_info(self, controller_id, controller_info):
        self.controllers[controller_id] = controller_info
        self.display_message("Controller: ({}) received with info\n{}".format(controller_id, controller_info))
        
    def remove_controller(self, controller_id):
        self.display_message("Controller: ({}) removed".format(controller_id))
        
    def update_all_sensor_info(self, controller_id, sensor_id, sensor_info):
        self.sensors[(controller_id, sensor_id)] = sensor_info
        self.display_message("Sensor: ({}:{}) received with info\n{}".format(controller_id, sensor_info['sensor_name'],
                                                                            str(sensor_info).replace(',', ',\n')))
    
    def update_sensor_info(self, controller_id, sensor_id, info_name, value):
        self.display_message("Sensor ({}:{}) had \'{}\' changed to {}".format(controller_id, sensor_id, info_name, value))
    
    def remove_sensor(self, controller_id, sensor_id):
        self.display_message("Sensor ({}:{}) removed".format(controller_id, sensor_id))
    
    def show_new_sensor_data(self, controller_id, sensor_id, data):
        self.display_message("Sensor ({}:{}) new data {}".format(controller_id, sensor_id, data))
    
    def append_sensor_message(self, controller_id, sensor_id, text):
        self.display_message("Sensor ({}:{}) new text {}".format(controller_id, sensor_id, text)) 
