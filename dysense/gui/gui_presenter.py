# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import zmq
import threading
import json
import os
import logging
import yaml

from PyQt4.QtCore import QObject, QTimer, QCoreApplication

from dysense.core.issue import Issue
from dysense.core.utility import json_dumps_unicode, make_unicode, make_utf8
from dysense.core.config_file import save_config_file, load_config_file

RECEIVE_TIMER_INTERVAL = 0.1 # seconds

class GUIPresenter(QObject):
    
    def __init__(self, manager_interface, metadata, view=None):
        
        super(GUIPresenter, self).__init__()
        
        self.manager_interface = manager_interface
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
                                  'controller_event': self.handle_controller_event,
                                  'controller_removed': self.handle_controller_removed,
                                  'error_message': self.handle_error_message,
                                  'new_controller_text': self.handle_new_controller_text,
                                  'new_source_data': self.handle_new_source_data,
                                  }
        
        self.manager_interface.register_callbacks(self.message_callbacks)
        self.manager_interface.setup()
       
    def setup_view(self, view):
        
        self.view = view
        
    def try_save_config(self, file_path):
        
        try:
            save_config_file(self, file_path)
        except:
            self.new_error_message("Unexpected error occurred when saving config.", logging.CRITICAL)
        
    def try_load_config(self, file_path):
        
        try:
            load_config_file(self, file_path)
        except:
            self.new_error_message("Unexpected error occurred when loading config.", logging.CRITICAL)
            
    def invalid_command_during_session(self, command_description):
        
        error_message = 'Cannot {} while session is active.'.format(command_description)
        self.new_error_message(error_message, logging.ERROR)
        
    def new_sensor_selected(self, controller_id, sensor_id):
        
        self.view.show_sensor(controller_id, sensor_id)    
    
    def new_controller_selected(self, controller_id):
    
        self.view.show_controller(controller_id)
    
    #called when user changes field in sensor view
    def sensor_view_field_changed(self, info_name, value, sensor_id):
    
        self.change_sensor_info(info_name, make_unicode(value))

    def connect_endpoint(self, manager_endpoint):
        
        self.manager_interface.connect_to_endpoint('manager', manager_endpoint)
        
    def update_active_sensor(self, active_controller_id, active_sensor_id):
        self.active_controller_id = active_controller_id
        self.active_sensor_id = active_sensor_id
        
    def add_controller(self, endpoint, name):

        self._send_message('add_controller', (endpoint, name))
        
    def controller_name_changed(self, new_controller_name):
        
        if new_controller_name.strip() == '':
            self.new_error_message("Controller name can't be empty string.", logging.ERROR)
            # 'Refresh' controller info to show the old name again.
            self.view.update_all_controller_info(self.local_controller['id'], self.local_controller)
            return
        
        question = 'Are you sure you want to change the controller ID?' \
        ' This is how other computers recognize this application and changing this ID can also affect saved configuration files.'
        if not self.view.confirm_question(question):
            # User doesn't want to.. so 'refresh' controller info to show the old name again.
            self.view.update_all_controller_info(self.local_controller['id'], self.local_controller)
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
        
    @property
    def active_controller(self):
        try:
            return self.controllers[self.active_controller_id]
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
        
        self.send_sensor_command_to_all_sensors('resume', None, only_on_active_controller)
    
    def pause_sensor(self):
    
        self.send_sensor_command('pause')
        
    def pause_all_sensors(self, only_on_active_controller):
        
        self.send_sensor_command_to_all_sensors('pause', None, only_on_active_controller)
    
    def close_sensor(self):
        
        self.send_sensor_command('close')
    
    def close_all_sensors(self, only_on_active_controller):
        
        self.send_sensor_command_to_all_sensors('close', None, only_on_active_controller)
        
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
        
        # TODO support multiple controllers - check through all sensors if send_to_all_controllers is true 
        if command_name == 'start_session' and not self.active_controller['session_active']:
            # Starting a session for the first time so warn if there are any issues.
            num_active_issues = len(self.active_controller['active_issues'])
            if num_active_issues > 0:
                if num_active_issues == 1:
                    question_start = "There is 1 unresolved issue"
                else:
                    question_start = "There are {} unresolved issues".format(len(self.active_controller['active_issues']))

                if not self.view.confirm_question(question_start + ". Do you want to start session anyways?"):
                    return
        
        if send_to_all_controllers:
            self._send_message_to_all_controllers('controller_command', (command_name, command_args))
        else:
            self._send_message_to_active_controller('controller_command', (command_name, command_args))

    def new_error_message(self, message, level):
        
        if level < logging.ERROR:
            return # don't care about this level

        self.view.show_user_message(message, level)

    def receive_messages(self):
        ''''''
        self.manager_interface.process_new_messages()
        
        # Constantly reschedule timer to avoid overlapping calls
        QTimer.singleShot(RECEIVE_TIMER_INTERVAL * 1000, self.receive_messages)

    #def change_sensor_parameter(self, parameter_name, value):   
    #   self._send_message_to_active_sensor('parameter_name', (parameter_name, value))

    def handle_entire_sensor_update(self, connection, controller_id, sensor_info):
        sensor_id = sensor_info['sensor_id']

        is_new_sensor = (controller_id, sensor_id) not in self.sensors
        
        self.sensors[(controller_id, sensor_id)] = sensor_info

        if is_new_sensor:
            self.view.add_new_sensor(controller_id, sensor_id, sensor_info)
        else:
            self.view.update_all_sensor_info(controller_id, sensor_id, sensor_info)                   
        
    def handle_sensor_changed(self, connection, controller_id, sensor_id, info_name, value): #this also applies to 'settings' where value = its dictionary
        #update the dictionary of sensors
        sensor_info = self.sensors[(controller_id, sensor_id)]
        sensor_info[info_name] = value
        
        self.view.update_sensor_info(controller_id, sensor_id, info_name, value)         
            
    def handle_sensor_removed(self, connection, controller_id, sensor_id):
        
        try:
            del self.sensors[(controller_id, sensor_id)]
        except KeyError:
            pass
        
        self.view.remove_sensor(controller_id, sensor_id)
    
    def handle_new_sensor_data(self, connection, controller_id, sensor_id, utc_time, sys_time, data, data_ok):
        self.view.show_new_sensor_data(controller_id, sensor_id, data)
    
    def handle_new_sensor_text(self, connection, controller_id, sensor_id, text):
        self.view.append_sensor_message(controller_id, sensor_id, text)
        
    def handle_entire_controller_update(self, connection, controller_info):
        
        controller_id = controller_info['id']
        
        is_new_controller = controller_id not in self.controllers
        
        self.controllers[controller_id] = controller_info
        
        if self.active_controller_id == None:
            self.active_controller_id = controller_id
        
        if is_new_controller:
            # TODO update for multiple controllers so is_local isn't always true
            self.view.add_new_controller(controller_id, controller_info, is_local=True)
            for issue_info in controller_info['active_issues']:
                self.current_issues.append(Issue(**issue_info))
            for issue_info in controller_info['resolved_issues']:
                self.old_issues.append(Issue(**issue_info))
            self.view.refresh_current_issues(self.current_issues)
                    
        self.view.update_all_controller_info(controller_info['id'], controller_info)

    def handle_controller_event(self, connection, controller_id, event_type, event_args):
        
        if event_type == 'session_started':
            pass 
        
        if event_type == 'session_ended':
            # Clear notes on screen since they would have been cleared in sensor controller.
            self.view.clear_session_notes(controller_id)
        
        if event_type == 'new_active_issue':
            issue_info = event_args
            self.current_issues.append(Issue(**issue_info))
            # TODO support multiple controllers
            if self.local_controller['session_active']:
                self.view.notify_new_issue(issue_info)
            self.view.refresh_current_issues(self.current_issues)
        
        if event_type == 'issue_resolved':
            issue_info = event_args
            for issue in self.current_issues[:]:
                if not issue.resolved and issue.matches(issue_info):
                    issue.resolved = True
                    issue.expiration_time = issue_info['end_time']
                    
                    if issue.acked:
                        self.current_issues.remove(issue)
                        self.old_issues.append(issue)
            self.view.refresh_current_issues(self.current_issues)
                    
        if event_type == 'issue_changed':
            issue_info = event_args
            for issue in self.current_issues:
                if not issue.resolved and issue.matches(issue_info):
                    issue.level = issue_info['level']
                    issue.reason = issue_info['reason']
            self.view.refresh_current_issues(self.current_issues)
        
        if event_type in ['extra_setting_added', 'extra_setting_removed']:
            self.view.extra_setting_added_or_removed(updated_extra_settings=event_args)
        
        if event_type == 'controller_crashed':

            message = "Oh no! Part of the program has crashed. If you had a session active don't worry it will be saved when the program closes.\n" \
                      "Please report the problem on the github issue tracker. To get a traceback of the problem " \
                      "check either the most recent debug log (located at ~/dysense_debug_logs/) or the session log if you had a session active."
            self.view.show_user_message(message, logging.CRITICAL)
            # This will cause app.exec_() to return.
            QCoreApplication.exit(1)
            
        if event_type == 'manager_crashed':
            # TODO This isn't really a controller event 
            message = "Oh no! Part of the program has crashed. If you had a session active don't worry it will be saved when the program closes.\n" \
                      "Please report this error on the github issue tracker.\nPress Ctrl+C to copy text from this dialog."
            for line in event_args:
                message += '\n' + line
            self.view.show_user_message(message, logging.CRITICAL)
            # This will cause app.exec_() to return.
            QCoreApplication.exit(1)
        
    def handle_controller_removed(self, connection, controller_id):
        self.view.remove_sensor(controller_id)
        
    def handle_error_message(self, connection, message, level):
        
        self.new_error_message(message, level)
    
    def handle_new_controller_text(self, connection, controller, text):
        self.view.display_message(text)
        
    def handle_new_source_data(self, connection, controller_id, sensor_id, source_type, utc_time, sys_time, data):
        
        if source_type == 'position':
            self.view.update_map(controller_id, sensor_id, source_type, utc_time, sys_time, data)
    
    def send_sensor_command(self, command_name, command_args=None):
    
        self._send_message_to_active_sensor('send_sensor_command', (command_name, command_args))
        
    def send_sensor_command_to_all_sensors(self, command_name, command_args, only_on_active_controller):
    
        self._send_message_to_all_sensors('send_sensor_command', (command_name, command_args), only_on_active_controller)
        
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

        # TODO don't hardcode manager ID
        self.manager_interface.send_message('manager', message_type, message_body)
            
    def close(self):
        
        self.manager_interface.close()
        
