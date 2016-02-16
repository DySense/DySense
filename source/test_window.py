
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
        
        # Should already have one controller (the local one on this computer).
        # The main API to the presenter is you set an active controller (and active sensor) and then most
        # of the methods you call are directed towards whatever's active.  So it's critical you keep those
        # 'active ids' in the presenter in-sync with what's on the screen.
        # Normally this 'setting active' would happen from user clicking on the controller in the tree view.
        self.presenter.active_controller_id = self.controllers.keys()[0]
        
        if self.test_step == 0:
            self.display_message("Telling presenter to add new sensor...")
            # If we don't include a 'settings' element then the controller will load the default values 
            # from the metadata file.  This sensor version must match what's in the metadata file.
            # Note this program is mostly asynchronous.  For example when 'add_sensor()' is called below
            # all it does is fires off a message and then immediately returns.  There's no instance feedback
            # to whether or not something worked or not. The message will be processed and sometime later
            # something else happens in return.  In this case update_all_sensor_info() will be called which
            # just means we received an entire sensor 'snapshot' of the new sensor.   The new 'snapshot' will
            # also contain a 'metadata' key which should contain everything from the metadata file for that
            # sensor type.  That's why so much stuff spits out after adding a sensor.. if you look through it
            # it's mostly metadata stuff.  It would probably be easiest to set a breakpoint and use the debugger
            # to view it's structure.  No promise that it's perfect.  Also sorry about the really long IDs for
            # the controllers.  It's a globally unique ID... this might change in the future but just assume it's
            # some unique string.  You'll notice sometimes the 'message center' says things change even though
            # they didn't change... that's because sometimes things change together e.g. sensor status the health
            # and state always change together, or the controller info always gets sent out all at once.  
            #new_sensor_info = {'version': '1.0',
            #                   'sensor_type': 'kinectv2_msdk',
            #                   'sensor_name': 'kinectv2_1'}
            new_sensor_info = {'version': '1.0',
                               'sensor_type': 'gps_nmea_test',
                               'sensor_name': 'test_sensor_name'}
            new_sensor_info['settings'] = {'test_file_path': r"C:\Users\Kyle\Documents\DySense\nmea_logs\SXBlueGGA.txt",
                                           'output_rate': 10,
                                           'required_fix': 'none',
                                           'required_precision': 0}
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
            self.start_button.setText('Close Sensor')
            
        if self.test_step == 5:
            
            self.display_message("Telling presenter to close active sensor...")
            self.presenter.close_sensor()
            self.start_button.setText('Remove Sensor')
            
        if self.test_step == 6:
            
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
