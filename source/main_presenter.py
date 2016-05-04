# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import zmq
import threading
import json
import os
import logging
import yaml
from ui_settings import ui_version
from PyQt4.QtCore import QObject, QTimer
from select_sources_window import SelectSourcesWindow
from add_sensor_window import AddSensorWindow
from end_session_dialog import EndSessionDialog
from issue import Issue
from utility import json_dumps_unicode, make_unicode, make_utf8

RECEIVE_TIMER_INTERVAL = 0.1 # seconds

class MainPresenter(QObject):
    
    def __init__(self, context, manager, metadata, view=None):
        
        super(MainPresenter, self).__init__()
        
        self.setup_logging()
        
        self.context = context
        self.manager = manager
        self.version = metadata['version']
        self.sensor_metadata = metadata['sensors']
        if view:
            self.setup_view(view)
        
        self.active_controller_id = None
        self.active_sensor_id = None
        
        # Issues corresponding to local controller. Old issues are ones that have been acked and resolved.
        self.current_issues = []
        self.old_issues = []
        
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
                                  'controller_issue_event': self.handle_controller_issue_event,
                                  'controller_removed': self.handle_controller_removed,
                                  'error_message': self.handle_error_message,
                                  'new_controller_text': self.handle_new_controller_text,
                                  'new_source_data': self.handle_new_source_data,
                                  }
        
        self.manager_socket = self.context.socket(zmq.DEALER)
       
    def setup_view(self, view):
        
        self.view = view
   
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
     
        log.info('DySense UI Version {}'.format(ui_version))
        
    def try_save_config(self, file_path):
        try:
            self.save_config(file_path)
        except:
            self.handle_error_message("Unexpected error occurred when saving config.", logging.CRITICAL)
        
    def save_config(self, file_path):
        '''Write current controller/sensors out to specified file path so the user can reload it later.'''
        # Data is what gets dumped to the file using yaml.
        data = {}
       
        controllers = []
        for controller_id, controller_info in self.controllers.iteritems():
            # TODO support multiple controllers
            useful_info = {}
            for info_name, info_value in controller_info.iteritems():
                if info_name in ['version', 'settings', 'time_source', 'position_sources', 'orientation_sources']:
                    useful_info[info_name] = info_value
            controllers.append(useful_info)
        data['controllers'] = controllers

        sensors = []
        for (sensor_id, controller_id), sensor_info in self.sensors.iteritems():
            # TODO save sensors in consistent order
            # TODO save sensors underneath controllers?
            useful_info = {}
            for info_name, info_value in sensor_info.iteritems():
                if info_name in ['sensor_type', 'sensor_id', 'settings', 'position_offsets', 'orientation_offsets', 'instrument_type', 'instrument_tag']:
                    useful_info[info_name] = info_value
            sensors.append(useful_info)
        data['sensors'] = sensors
    
        with open(file_path, 'w') as outfile:
            outfile.write(yaml.safe_dump(data, allow_unicode=True, default_flow_style=False))
        
    def try_load_config(self, file_path):
        try:
            self.load_config(file_path)
        except:
            self.handle_error_message("Unexpected error occurred when loading config.", logging.CRITICAL)
        
    def load_config(self, file_path):
        '''Load controller/sensors out of specified yaml file path.'''
        
        if not os.path.exists(file_path):
            self.handle_error_message("Config file '{}' does not exist.".format(file_path), logging.ERROR)
            return
        
        # TODO remove other controllers (and their sensors?) once that's all supported
        self.remove_all_sensors(only_on_active_controller=True)
        
        with open(file_path, 'r') as stream:
            data = yaml.load(stream)
        
        # TODO support multiple controllers
        if len(self.controllers) == 0:
            self.handle_error_message("Need at least one controller before loading config", logging.ERROR)
            return
        
        # Request that all data stored in saved controller info gets set to the active controller (which right now is the only allowed controller)
        for saved_controller_info in data.get('controllers', []):
            for info_name, info_value in saved_controller_info.iteritems():
                if info_name == 'settings':
                    for setting_name, setting_value in info_value.iteritems():
                        self.change_controller_setting(setting_name, setting_value)
                elif info_name == 'version':
                    pass # TODO verify program version matches config version
                else:
                    self.change_controller_info(info_name, info_value) 
                    
        # Request that all saved sensors get added to the active controller (which right now is the only allowed controller)
        for saved_sensor_info in data.get('sensors', []):
            self.add_sensor(saved_sensor_info)
        
    def new_sensor_selected(self, controller_id, sensor_id):
        
        self.view.show_sensor(controller_id, sensor_id)    
    
    def new_controller_selected(self, controller_id):
    
        self.view.show_controller(controller_id)
    
    #called when user changes field in sensor view
    def sensor_view_field_changed(self, info_name, value, sensor_id):
    
        self.change_sensor_info(info_name, make_unicode(value))

    def connect_endpoint(self, manager_endpoint):
        
        self.manager_socket.connect(manager_endpoint)
        
    def update_active_sensor(self, active_controller_id, active_sensor_id):
        self.active_controller_id = active_controller_id
        self.active_sensor_id = active_sensor_id
        
    def add_controller(self, endpoint, name):

        self._send_message('add_controller', (endpoint, name))
        
    def end_session(self):
        
        # TODO update for multiple controllers
        self.end_session_dialog = EndSessionDialog(self, self.controllers.values()[0])
        self.end_session_dialog.setModal(True)
        self.end_session_dialog.show()
        
    def select_data_sources(self):
        
        active_controller = self.controllers[self.active_controller_id]
        
        self.select_sources_window = SelectSourcesWindow(self, active_controller, self.sensors)
        self.select_sources_window.setModal(True)
        self.select_sources_window.show()
        
    def add_sensor_requested(self):
        
        possible_sensor_types = sorted(self.sensor_metadata.keys())
        sensor_id_types = [self.sensor_metadata[sensor_type]['type'] for sensor_type in possible_sensor_types]
        
        self.add_sensor_window = AddSensorWindow(self, possible_sensor_types, sensor_id_types)
        self.add_sensor_window.setModal(True)
        self.add_sensor_window.show()
        
    def controller_name_changed(self, new_controller_name):
        
        if new_controller_name.strip() == '':
            self.handle_error_message("Controller name can't be empty string.", logging.ERROR)
            return
        
        self.view.local_controller_name = new_controller_name
        
        self.view.show_user_message('New controller name will take effect once application is restarted.', logging.INFO)
        
    @property
    def local_controller(self):
        try:
            # TODO update for multiple controllers
            return self.controllers.values()[0]
        except IndexError:
            return None 
        
    def change_controller_info(self, info_name, info_value):
        
        self._send_message_to_active_controller('change_controller_info', (info_name, info_value))
        
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
        
    def acknowledge_issue_by_index(self, issue_idx):
        try:
            issue_info = self.current_issues[issue_idx].public_info
            self.acknowledge_issue(issue_info)
        except IndexError:
            pass
        
    def acknowledge_issue(self, issue_info, ack_all_issues=False):
        for issue in self.current_issues[:]:
            if ack_all_issues or issue.matches(issue_info):
                issue.acked = True
                if issue.resolved:
                    self.current_issues.remove(issue)
                    self.old_issues.append(issue)
                    
        self.view.refresh_current_issues(self.current_issues)
        
    def send_controller_command(self, command_name, command_args=None, send_to_all_controllers=False):
        
        if send_to_all_controllers:
            self._send_message_to_all_controllers('controller_command', (command_name, command_args))
        else:
            self._send_message_to_active_controller('controller_command', (command_name, command_args))

    def receive_messages(self):
        ''''''
        self.process_new_messages()
        
        # Constantly reschedule timer to avoid overlapping calls
        QTimer.singleShot(RECEIVE_TIMER_INTERVAL * 1000, self.receive_messages)

    #def change_sensor_parameter(self, parameter_name, value):   
    #   self._send_message_to_active_sensor('parameter_name', (parameter_name, value))

    def handle_entire_sensor_update(self, controller_id, sensor_info):
        sensor_id = sensor_info['sensor_id']

        is_new_sensor = (controller_id, sensor_id) not in self.sensors
        
        self.sensors[(controller_id, sensor_id)] = sensor_info

        if is_new_sensor:
            self.view.add_new_sensor(controller_id, sensor_id, sensor_info)
        else:
            self.view.update_all_sensor_info(controller_id, sensor_id, sensor_info)                   
        
    def handle_sensor_changed(self, controller_id, sensor_id, info_name, value): #this also applies to 'settings' where value = its dictionary
        #update the dictionary of sensors
        sensor_info = self.sensors[(controller_id, sensor_id)]
        sensor_info[info_name] = value
        
        self.view.update_sensor_info(controller_id, sensor_id, info_name, value)         
            
    def handle_sensor_removed(self, controller_id, sensor_id):
        
        try:
            del self.sensors[(controller_id, sensor_id)]
        except KeyError:
            pass
        
        self.view.remove_sensor(controller_id, sensor_id)
    
    def handle_new_sensor_data(self, controller_id, sensor_id, utc_time, sys_time, data, data_ok):
        self.view.show_new_sensor_data(controller_id, sensor_id, data)
    
    def handle_new_sensor_text(self, controller_id, sensor_id, text):
        self.view.append_sensor_message(controller_id, sensor_id, text)
        
    def handle_entire_controller_update(self, controller_info):
        
        controller_id = controller_info['id']
        
        is_new_controller = controller_id not in self.controllers
        
        self.controllers[controller_id] = controller_info
        
        if self.active_controller_id == None:
            self.active_controller_id = controller_id
        
        if is_new_controller:
            self.view.add_new_controller(controller_id, controller_info)
            for issue_info in controller_info['active_issues']:
                self.current_issues.append(Issue(**issue_info))
            for issue_info in controller_info['resolved_issues']:
                self.old_issues.append(Issue(**issue_info))
            self.view.refresh_current_issues(self.current_issues)
                    
        self.view.update_all_controller_info(controller_info['id'], controller_info)

    def handle_controller_issue_event(self, controller_id, event_type, issue_info):
        
        if event_type == 'new_active_issue':
            self.current_issues.append(Issue(**issue_info))
            # TODO support multiple controllers
            if self.local_controller['session_active']:
                self.view.notify_new_issue(issue_info)
        
        if event_type == 'issue_resolved':
            for issue in self.current_issues[:]:
                if not issue.resolved and issue.matches(issue_info):
                    issue.resolved = True
                    issue.expiration_time = issue_info['end_time']
                    
                    if issue.acked:
                        self.current_issues.remove(issue)
                        self.old_issues.append(issue)
                    
                    
        if event_type == 'issue_changed':
            for issue in self.current_issues:
                if not issue.resolved and issue.matches(issue_info):
                    issue.level = issue_info['level']
                    issue.reason = issue_info['reason']
        
        self.view.refresh_current_issues(self.current_issues)
        
    def handle_controller_removed(self, controller_id):
        self.view.remove_sensor(controller_id)
        
    def handle_error_message(self, message, level):
        
        if level < logging.ERROR:
            return # don't care about this level
        
        logging.getLogger("ui").log(level, message)
        
        self.view.show_user_message(message, level)
    
    def handle_new_controller_text(self, controller, text):
        self.view.display_message(text)
        
    def handle_new_source_data(self, controller_id, sensor_id, source_type, utc_time, sys_time, data):
        
        if source_type == 'position':
            # TODO update map (system time passed in as argument to this callback)
            #print "{} {} {} {} {}".format(controller_id, sensor_id, utc_time, sys_time, data)
            pass
    
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

        self.manager_socket.send(json_dumps_unicode({'type': message_type, 'body': message_body}))

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
        
