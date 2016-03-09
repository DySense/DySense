#!/usr/bin/env python

import time
import zmq
import threading
import json
import os
import logging

from PyQt4.QtCore import QObject, QTimer

RECEIVE_TIMER_INTERVAL = 0.1 # seconds

class MainPresenter(QObject):
    
    def __init__(self, context, manager, metadata, view=None):
        
        super(MainPresenter, self).__init__()
        
        self.setup_logging()
        
        self.context = context
        self.manager = manager
        self.version = metadata['version']
        self.sensor_metadata = metadata['sensors']
        self.view = view
        
        self.active_controller_id = None
        self.active_sensor_id = None
        

        # Lookup table of controller information.
        # key - controller id 
        # value - dictionary of controller info.
        self.controllers = {}
        
        # Lookup table of sensor information.
        # key - tuple of (controller id, sensor id)
        # value - dictionary of sensor info.
        self.sensors = {}        
        
        
        
        self.message_callbacks = { # From Manager
                                  'entire_sensor_update': self.handle_entire_sensor_update,
                                  'sensor_changed': self.handle_sensor_changed,
                                  'sensor_removed': self.handle_sensor_removed,
                                  'new_sensor_data': self.handle_new_sensor_data,
                                  'new_sensor_text': self.handle_new_sensor_text,
                                  'entire_controller_update': self.handle_entire_controller_update,
                                  'controller_removed': self.handle_controller_removed,
                                  'error_message': self.handle_error_message,
                                  }
        
        self.manager_socket = self.context.socket(zmq.DEALER)
       
 
   
    def setup_logging(self):
      
        
        # Use home directory for root output directory. This is platform independent and works well with an installed package.
        home_directory = os.path.expanduser('~')
        output_directory = os.path.join(home_directory, 'dysense_logs/')
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        
        # Create logger at lowest level since each handler will define its own level which will further filter.
        log = logging.getLogger("ui")
        log.setLevel(logging.DEBUG)
        
        # Add handler to record information to a log file.
        handler = logging.FileHandler(os.path.join(output_directory, time.strftime("%Y-%m-%d_%H-%M-%S_ui_log.log")))
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s'))
        log.addHandler(handler)
     
        # TODO reference version number once that's setup
        log.info('DySense UI Version {}'.format(1.0))
        
    def new_sensor_selected(self, controller_id, sensor_id):
        
        #call show_sensor to set the active sensor id and set the correct widget to front
        self.view.show_sensor(sensor_id)    
         
    
    #called when user changes field in sensor view
    def sensor_view_field_changed(self, info_name, value, sensor_id):
    
        self.change_sensor_info(info_name, str(value))
        # calling self.change_sensor yields TypeError: PyQt4.QtCore.QString(u'sensor2') is not JSON serializable
        
        
        #if the value changed is sensor name, call function to update the name in the sensor list
        if info_name == 'sensor_name':
            self.view.sensor_name_changed(value, sensor_id)           
        
    
        
    def connect_endpoint(self, manager_endpoint):
        
        self.manager_socket.connect(manager_endpoint)
        
    def update_active_sensor(self, active_controller_id, active_sensor_id):
        self.active_controller_id = active_controller_id
        self.active_sensor_id = active_sensor_id
        
    def add_controller(self, endpoint, name):

        self._send_message('add_controller', (endpoint, name))
        
    def change_controller_data_source(self, data_source_name, sensor_id, controller_id):
        
        # We need to provide the metadata since the controller might not know anything about the sensor.
        # TODO - need to change this to just self.sensors once Ethan merges in changes
        source_metadata = self.view.sensors[(controller_id, sensor_id)]['metadata']
        
        new_source = {"controller_id": controller_id, "sensor_id": sensor_id, 'metadata': source_metadata}

        self._send_message_to_active_controller('change_data_source', (data_source_name, new_source))
        
    def remove_controller(self, controller_id):

        self._send_message('remove_controller', controller_id)

    def add_sensor(self, sensor_info):
        
        self._send_message_to_active_controller('add_sensor', sensor_info)
        
    def remove_sensor(self, sensor_id):
        
        self._send_message_to_active_controller('remove_sensor', sensor_id)
        
    def remove_all_sensors(self, only_on_active_controller):
        
        if only_on_active_controller:
            self._send_message_to_active_controller('remove_sensor', 'all')
        else:
            self._send_message_to_all_controllers('remove_sensor', 'all')
    
    def setup_sensor(self):
        
        self._send_message_to_active_sensor('setup_sensor', '')
    
    def setup_all_sensors(self, only_on_active_controller):
        
        self._send_message_to_all_sensors('setup_sensor', '', only_on_active_controller)
    
    def resume_sensor(self):
    
        self.send_sensor_command('resume')
        
    def resume_all_sensors(self, only_on_active_controller):
        
        self._send_message_to_all_sensors('send_sensor_command', 'resume', only_on_active_controller)
    
    def pause_sensor(self):
    
        self.send_sensor_command('pause')
        
    def pause_all_sensors(self, only_on_active_controller):
        
        self._send_message_to_all_sensors('send_sensor_command', 'pause', only_on_active_controller)
    
    def close_sensor(self):
        
        self._send_message_to_active_sensor('send_sensor_command', 'close')
    
    def close_all_sensors(self, only_on_active_controller):
        
        self._send_message_to_all_sensors('send_sensor_command', 'close', only_on_active_controller)
        
    
    def change_sensor_info(self, info_name, value):
        
        self._send_message_to_active_sensor('change_sensor_info', (info_name, value))
    
    
    def change_sensor_setting(self, setting_name, value):
        
        self._send_message_to_active_sensor('change_sensor_setting', (setting_name, value))

    def change_controller_setting(self, setting_name, value):        
        
        self._send_message_to_active_controller('change_controller_setting', (setting_name, value))
        
    def send_controller_command(self, command_name, send_to_all_controllers):
        
        if send_to_all_controllers:
            self._send_message_to_all_controllers('controller_command', command_name)
        else:
            self._send_message_to_active_controller('controller_command', command_name)

    def receive_messages(self):
        ''''''
        self.process_new_messages()
        
        # Constantly reschedule timer to avoid overlapping calls
        QTimer.singleShot(RECEIVE_TIMER_INTERVAL * 1000, self.receive_messages)

    #def change_sensor_parameter(self, parameter_name, value):   
    #   self._send_message_to_active_sensor('parameter_name', (parameter_name, value))

    def handle_entire_sensor_update(self, controller_id, sensor_info):
        sensor_id = sensor_info['sensor_id']
        sensor_name = sensor_info['sensor_name'] 
        
        #if sensor is not already stored 
        if (controller_id, sensor_id) not in self.sensors:
            #add sensor info to sensors dict
            self.sensors[(controller_id, sensor_id)] = sensor_info
            #creates the new sensor view which then calls view.update_all_sensor_info
            self.view.create_new_sensor_view(controller_id, sensor_id, sensor_info)
            self.view.add_sensor_to_list_widget(controller_id, sensor_id, sensor_name)
                                      
        else:
            self.view.update_all_sensor_info(controller_id, sensor_id, sensor_info)                   
        
        
        
    def handle_sensor_changed(self, controller_id, sensor_id, info_name, value): #this also applies to 'settings' where value = its dictionary
        #update the dictionary of sensors
        sensor_info = self.sensors[(controller_id, sensor_id)]
        sensor_info[info_name] = value
        
        self.view.update_sensor_info(controller_id, sensor_id, info_name, value)
        
        if info_name == 'sensor_name':
            self.view.update_sensor_list_widget(controller_id, sensor_id, value)
            
    def handle_sensor_removed(self, controller_id, sensor_id):
        self.view.remove_sensor(controller_id, sensor_id)
    
    def handle_new_sensor_data(self, controller_id, sensor_id, data):
        self.view.show_new_sensor_data(controller_id, sensor_id, data)
    
    def handle_new_sensor_text(self, controller_id, sensor_id, text):
        self.view.append_sensor_message(controller_id, sensor_id, text)
        
    def handle_entire_controller_update(self, controller_info):
        
        controller_id = controller_info['id']
        
        if controller_id not in self.controllers:
            self.controllers[controller_id] = controller_info
        
        if self.active_controller_id == None:
            self.active_controller_id = controller_id
            
        self.view.update_all_controller_info(controller_info['id'], controller_info)
        
    def handle_controller_removed(self, controller_id):
        self.view.remove_sensor(controller_id)
        
    def handle_error_message(self, message, level):
        
        if level < logging.ERROR:
            return # don't care about this level
        
        logging.getLogger("ui").log(level, message)
        
        self.view.show_error_message(message, level)
    
    def send_sensor_command(self, command):
    
        self._send_message_to_active_sensor('send_sensor_command', command)
        
    def _send_message_to_active_sensor(self, message_type, message_body):
        self._send_message_to_sensor(message_type, message_body, self.active_sensor_id, self.active_controller_id)
        
    def _send_message_to_all_sensors(self, message_type, message_body, only_on_active_controller=True):
        controller_id = self.active_controller_id if only_on_active_controller else 'all'
        self._send_message_to_sensor(message_type, message_body, 'all', controller_id)

    def _send_message_to_sensor(self, sensor_message_type, sensor_message_body, sensor_id, controller_id):
        message_body = (sensor_id, sensor_message_body)
        self._send_message_to_controller(sensor_message_type, message_body, controller_id)
        
    def _send_message_to_active_controller(self, message_type, message_body):
        self._send_message_to_controller(message_type, message_body, self.active_controller_id)
        
    def _send_message_to_all_controllers(self, message_type, message_body):
        self._send_message_to_controller(message_type, message_body, 'all')
        
    def _send_message_to_controller(self, controller_message_type, controller_message_body, controller_id):
        controller_message = {'type': controller_message_type, 'body': controller_message_body}
        message_body = (self.active_controller_id, controller_message)
        self._send_message('forward_to_controller', message_body)

    def _send_message(self, message_type, message_body):

        self.manager_socket.send(json.dumps({'type': message_type, 'body': message_body}))

    def process_new_messages(self):
        
        while True:
            try:
                message = json.loads(self.manager_socket.recv(zmq.NOBLOCK))
                message_body = message['body']
                message_callback = self.message_callbacks[message['type']]
                if isinstance(message_body, (tuple, list)):
                    message_callback(*message_body)
                else:
                    message_callback(message_body)
            except zmq.ZMQError:
                break # no more messages right now
            
    def close(self):
        
        self.manager.stop_request.set()
        
        self.manager_socket.close()
        
