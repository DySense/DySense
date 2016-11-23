# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import time
import zmq
import json
import threading
import datetime
import sys
import logging
import yaml
import csv
import traceback

from dysense.core.sensor_connection import SensorConnection
from dysense.core.sensor_creation import SensorDriverFactory, SensorCloseTimeout
from dysense.core.csv_log import CSVLog
from dysense.core.controller_data_sources import *
from dysense.core.issue import Issue
from dysense.core.utility import format_id, json_dumps_unicode, utf_8_encoder
from dysense.core.utility import make_unicode, make_utf8, validate_type, make_filename_unique
from dysense.core.version import app_version, output_version
from dysense.core.session import Session

class SensorController(object):
    
    def __init__(self, context, metadata, controller_id, sensor_interface, manager_interface):
        
        self.setup_logging()
        
        self.context = context
        
        self.sensor_metadata = metadata['sensors']
        
        self.sensors = []
        self.managers = {}
        
        self.text_messages = []
        
        self._time_source = None
        self._position_sources = []
        self._orientation_sources = []
        self._height_sources = []
        self._fixed_height_source = None
        
        self.controller_id = format_id(controller_id) 
        
        self.sensor_interface = sensor_interface
        self.manager_interface = manager_interface
        
        self.session = Session(self)
        
        self.active_issues = []
        self.resolved_issues = []        
        
        self.settings = {'base_out_directory': '',
                         'operator_name': '',
                         'platform_type': '',
                         'platform_tag': '',
                         'experiment_id': '',
                         'surveyed': True}
        
        # Allow settings to optionally define a type (e.g. bool) that will be enforced. 
        self.setting_name_to_type = {'surveyed': 'bool'}
        
        self.stop_request = threading.Event()
        
        # The last manager that a message was received from.
        self.last_manager = None
        
        # Last received utc time and the corresponding sys time it was updated.
        self.last_utc_time = 0.0
        self.last_sys_time_update = 0.0
        
        # Used for timing test dealing with message passing.
        self.time_test_durations = []
        
        # Used for creating new sensor drivers. Can't instantiate it until we know what endpoints we're bound to.
        self.sensor_driver_factory = None
        
        # Set to true when trying to stop session to detect if that's what's throwing an exception.
        self.stopping_session = False
        
        self.message_callbacks = { # From Managers
                                  'request_connect': self.handle_request_connect,
                                  'add_sensor': self.handle_add_sensor,
                                  'remove_sensor': self.handle_remove_sensor,
                                  'request_sensor': self.handle_request_sensor,
                                  'setup_sensor': self.handle_setup_sensor,
                                  'change_sensor_info': self.handle_change_sensor_info,
                                  'change_sensor_setting': self.handle_change_sensor_setting,
                                  'send_sensor_command': self.handle_send_sensor_command,
                                  'change_controller_info': self.handle_change_controller_info,
                                  'change_controller_setting': self.handle_change_controller_setting,
                                  'new_data_source_data': self.handle_data_source_data,
                                  'controller_command': self.handle_controller_command,
                                  
                                   # From Sensors
                                  'new_sensor_data': self.handle_new_sensor_data,
                                  'new_sensor_text': self.handle_new_sensor_text,
                                  'new_sensor_status': self.handle_new_sensor_status,
                                  'new_sensor_heartbeat': self.handle_new_sensor_heartbeat,
                                  'new_sensor_event': self.handle_new_sensor_event,
                                  }
        
        # Register callbacks with interface.
        self.sensor_interface.register_callbacks(self.message_callbacks)
        self.sensor_interface.heartbeat_period = 0.5 # seconds
        
        # TODO split callbacks up
        self.manager_interface.register_callbacks(self.message_callbacks)

    @property
    def public_info(self):
        return {'id': self.controller_id,
                'session_state': self.session.state,
                'session_active': self.session.active,
                'session_name': self.session.name,
                'session_path': self.session.path,
                'time_source': None if not self.time_source else self.time_source.public_info,
                'position_sources': [source.public_info for source in self.position_sources],
                'orientation_sources': [source.public_info for source in self.orientation_sources],
                'height_sources': [source.public_info for source in self.height_sources],
                'fixed_height_source': self.fixed_height_source,
                'settings': self.settings,
                'text_messages': self.text_messages,
                'active_issues': [source.public_info for source in self.active_issues],
                'resolved_issues': [source.public_info for source in self.resolved_issues],
                }
    
    @property
    def time_source(self):
        return self._time_source
    @time_source.setter
    def time_source(self, new_value):
        if new_value is None:
            self._time_source = None
        else:
            self._time_source = TimeDataSource(self.send_entire_controller_info, **new_value)
        self.send_entire_controller_info()
        
    @property
    def position_sources(self):
        return self._position_sources
    @position_sources.setter
    def position_sources(self, new_value):
        self._position_sources = []
        for val in new_value:
            self._position_sources.append(PositionDataSource(self.send_entire_controller_info, **val))
        self.send_entire_controller_info()
        
    @property
    def orientation_sources(self):
        return self._orientation_sources
    @orientation_sources.setter
    def orientation_sources(self, new_value):
        self._orientation_sources = []
        angle_types = ['roll', 'pitch', 'yaw']
        for n, val in enumerate(new_value):
            self._orientation_sources.append(OrientationDataSource(self.send_entire_controller_info, angle_types[n], **val))
        self.send_entire_controller_info()
        
    @property
    def height_sources(self):
        return self._height_sources
    @height_sources.setter
    def height_sources(self, new_value):
        self._height_sources = []
        for val in new_value:
            self._height_sources.append(HeightDataSource(self.send_entire_controller_info, **val))
        self.send_entire_controller_info()
        
    @property
    def all_sources(self):
        return [self.time_source] + self.position_sources + self.orientation_sources + self.height_sources
        
    @property
    def fixed_height_source(self):
        return self._fixed_height_source
    @fixed_height_source.setter
    def fixed_height_source(self, new_value):
        
        if make_unicode(new_value).strip() == "":
            self._fixed_height_source = None
        else:
            try:
                self._fixed_height_source = validate_type(new_value, 'float')
            except ValueError:
                self.log_message("{} is not a valid height measurement.".format(new_value), logging.ERROR, self.last_manager)
            
        self.send_entire_controller_info()
        
    def setup_logging(self):
        
        # Use home directory for root output directory. This is platform independent and works well with an installed package.
        home_directory = os.path.expanduser('~')
        output_directory = os.path.join(home_directory, 'dysense_debug_logs/')
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        
        # Create logger to write out to a file.
        log = logging.getLogger("dysense")
        log.setLevel(logging.DEBUG)
        #handler = logging.StreamHandler(sys.stdout)
        handler = logging.FileHandler(os.path.join(output_directory, time.strftime("%Y-%m-%d_%H-%M-%S_dysense_log.log")))
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s'))
        log.addHandler(handler)
        
    def log_message(self, msg, level=logging.INFO, manager=None):
        
        # Sanity check that message is unicode like it should be.
        msg = make_unicode(msg)
        
        logging.getLogger('dysense').log(level, msg)
        
        session_log = logging.getLogger('session')
        if len(session_log.handlers) > 0:
            session_log.log(level, msg)
        
        if manager is not None and level >= logging.ERROR:
            manager.send_message('error_message', (msg, level))
            
        if level >= logging.INFO:
            self.text_messages.append(msg)
            self.manager_interface.send_message_to_all('new_controller_text', msg)
        
    def run(self):

        try:
            self.setup()
            self.run_message_loop()
        except Exception as e:
            formatted_lines = traceback.format_exc().splitlines()
            traceback_lines = formatted_lines[:-1] 

            error_lines = []
            error_lines.append("------------")
            error_lines.append("{} - {}".format(type(e).__name__, make_unicode(e)))
            for traceback_line in traceback_lines:
                error_lines.append(traceback_line)
            error_lines.append("------------")

            # Log each line separately so shows up with newlines in log(s).
            for error_line in error_lines:
                self.log_message(error_line, level=logging.CRITICAL)
                
            # Notify everyone that this controller crashed.
            self.manager_interface.send_message_to_all('controller_event', ('controller_crashed', None))
            
        finally:
            self.close_down()

    def setup(self):
        
        # Use a poller to receive from multiple interfaces, and to allow timeouts when waiting.
        # Note this must be done BEFORE setting up interfaces so that sockets will be registered correctly.
        self.poller = zmq.Poller()
        self.sensor_interface.register_poller(self.poller)
        self.manager_interface.register_poller(self.poller)
        
        # Now that thread is started can setup interfaces.
        self.sensor_interface.setup()
        self.manager_interface.setup()
        
        # Need to do this after remote endpoint is determined.
        self.sensor_driver_factory = SensorDriverFactory(self.context,
                                                         self.sensor_interface.local_endpoint,
                                                         self.sensor_interface.remote_endpoint)

    def run_message_loop(self):
    
        # How often to run slower rate 'update' loop.
        update_loop_interval = 0.1
        next_update_loop_time = time.time()
    
        # Timeout when waiting for new messages.
        message_timeout = 500  # milliseconds
    
        while True:
            
            if self.stop_request.is_set():
                break  # from main loop
            
            self.process_new_messages(message_timeout)

            current_time = time.time()
            if current_time >= next_update_loop_time:
                
                for sensor in self.sensors:
                    sensor.refresh_state()
                    
                for issue in self.active_issues[:]:
                    if issue.expired:
                        self.active_issues.remove(issue)
                        self.resolved_issues.append(issue)
                        self.send_controller_issue_event('issue_resolved', issue)
                        self.send_entire_controller_info()

                # TODO make this more efficient when receiving sources we're not constantly trying to resolve issues that don't exist.
                if self.session.active:
                    if self.time_source and not self.time_source.receiving:
                        self.try_create_issue(self.controller_id, self.time_source.sensor_id, 'lost_time_source', 'Not receiving data from time source.', 'critical')
                    elif self.time_source:
                        self.try_resolve_issue(self.time_source.sensor_id, 'lost_time_source')
                    for source in self.position_sources:
                        if not source.receiving:
                            self.try_create_issue(self.controller_id, source.sensor_id, 'lost_position_source', 'Not receiving data from position source.', 'critical')
                        else:
                            self.try_resolve_issue(source.sensor_id, 'lost_position_source')
                    for source in self.orientation_sources:
                        if not source.receiving:
                            self.try_create_issue(self.controller_id, source.sensor_id, 'lost_orientation_source', 'Not receiving data from orientation source.', 'critical')
                        else:
                            self.try_resolve_issue(source.sensor_id, 'lost_orientation_source')
                    for source in self.height_sources:
                        if not source.receiving:
                            self.try_create_issue(self.controller_id, source.sensor_id, 'lost_height_source', 'Not receiving data from height source.', 'critical')
                        else:
                            self.try_resolve_issue(source.sensor_id, 'lost_height_source')
                else: 
                    # TODO make this more efficient when receiving sources we're not constantly trying to resolve issues that don't exist. 
                    if self.time_source:
                        self.try_resolve_issue(self.time_source.sensor_id, 'lost_time_source')
                    for source in self.position_sources:
                        self.try_resolve_issue(source.sensor_id, 'lost_position_source')
                    for source in self.orientation_sources:
                        self.try_resolve_issue(source.sensor_id, 'lost_orientation_source')
                    for source in self.height_sources:
                        self.try_resolve_issue(source.sensor_id, 'lost_height_source')
                            
                self.session.update_state()
                
                next_update_loop_time = current_time + update_loop_interval
            
    def close_down(self):

        self.log_message("Controller closing down.")
        
        if self.session.active and not self.stopping_session:
            self.stop_session(manager=None, interrupted=True)
        
        for sensor in self.sensors:
            self.close_down_sensor(sensor)
            
        self.manager_interface.close()
        self.sensor_interface.close()
            
    def close_down_sensor(self, sensor):
        
        try:
            sensor.close()
        except SensorCloseTimeout:
            pass  # TODO notify managers that sensor failed to close down.
            
    def process_new_messages(self, timeout):

        msgs = dict(self.poller.poll(timeout)) 

        self.sensor_interface.process_new_messages()  
        self.manager_interface.process_new_messages()

    def send_entire_controller_info(self):
    
        self.manager_interface.send_message_to_all('entire_controller_update', self.public_info)
        
    def send_controller_issue_event(self, event_type, issue):
    
        self.manager_interface.send_message_to_all('controller_event', (event_type, issue.public_info))
        
    def send_session_event(self, event_type, event_args=None):
    
        self.manager_interface.send_message_to_all('controller_event', (event_type, event_args))
        
    def send_entire_sensor_info(self, sensor):
    
        self.manager_interface.send_message_to_all('entire_sensor_update', sensor.public_info)
        
    def handle_request_connect(self, manager, unused):
        
        self.send_entire_controller_info()
        
        for sensor in self.sensors:
            manager.send_message('entire_sensor_update', sensor.public_info)
            
        self.log_message('Connected to manager.', logging.DEBUG)
        
    def handle_add_sensor(self, manager, sensor_info):
        '''Validate that sensor name is unique and adds to list of sensors.'''

        if self.session.active:
            self.log_message('Cannot add sensor while session is active.', logging.ERROR, manager)
            return
        
        if sensor_info['sensor_type'] not in self.sensor_metadata:
            self.log_message('Cannot add sensor with type {} because it does not exist in metadata.'.format(sensor_info['sensor_type']), logging.ERROR, manager)
            return
        
        # Get metadata that was stored with this controller.
        metadata = self.sensor_metadata[sensor_info['sensor_type']]
        
        sensor_name = format_id(make_unicode(sensor_info['sensor_id']))
        sensor_type = make_unicode(sensor_info['sensor_type']).strip()
        position_offsets = sensor_info.get('position_offsets', [0, 0, 0])
        orientation_offsets = sensor_info.get('orientation_offsets', [0, 0, 0])
        instrument_type = make_unicode(sensor_info.get('instrument_type', 'NONE')).replace(' ','')
        instrument_tag = format_id(make_unicode(sensor_info.get('instrument_tag', '123')))
        
        settings = {}
        for setting_metadata in metadata['settings']:
            setting_name = setting_metadata['name']
            try:
                settings_value = make_unicode(sensor_info['settings'][setting_name])
            except KeyError:
                # User didn't provide this setting so try to use the default value.
                try:
                    settings_value = setting_metadata['default_value']
                except KeyError:
                    settings_value = None
        
            settings[setting_name] = settings_value 
        
        if sensor_name == '':
            self.log_message("Need to provide a non-empty sensor name.", logging.ERROR, manager)
            return
        
        if instrument_tag == '':
            self.log_message("Need to provide a non-empty instrument tag (ID).", logging.ERROR, manager)
            return
        
        if sensor_name != self._make_sensor_name_unique(sensor_name):
            self.log_message("Cannot add sensor '{}' because there's already a sensor with that name.".format(sensor_name), logging.ERROR, manager)
            return
            
        new_sensor = SensorConnection(self.sensor_interface, metadata['version'], sensor_name, self.controller_id, sensor_type,
                                      settings, position_offsets, orientation_offsets, instrument_type, instrument_tag,
                                      metadata, self, self.sensor_driver_factory)
        
        self.sensors.append(new_sensor)
        
        self.send_entire_sensor_info(new_sensor)
        
        # Validate all settings once sensor has been sent to all managers.
        new_sensor.validate_settings()
        
        self.log_message("Added new sensor {} ({}).".format(sensor_name, sensor_type), logging.DEBUG)

    def handle_remove_sensor(self, manager, sensor_id):
        '''Search through sensors and remove one that has matching id.'''
        
        if self.session.active:
            self.log_message('Cannot remove sensor while session is active.', logging.ERROR, manager)
            return 
        
        if sensor_id == 'all':
            sensors = self.sensors
        else:
            sensors = [self.find_sensor(sensor_id)]
        
        for sensor in sensors[:]:
            self.close_down_sensor(sensor)
            self.sensors.remove(sensor)
            self.manager_interface.send_message_to_all('sensor_removed', sensor.sensor_id)
            
            self.log_message("Removed sensor {} ({})".format(sensor.sensor_id, sensor.sensor_type), logging.DEBUG)
            
            # Remove any data sources that match up with the removed sensor.
            if self.time_source and self.time_source.matches(sensor.sensor_id, self.controller_id):
                self.time_source = None
            for source in self.position_sources[:]:
                if source.matches(sensor.sensor_id, sensor.controller_id):
                    self.position_sources.remove(source)
            for source in self.orientation_sources[:]:
                if source.matches(sensor.sensor_id, sensor.controller_id):
                    self.orientation_sources.remove(source)
            for source in self.height_sources[:]:
                if source.matches(sensor.sensor_id, sensor.controller_id):
                    self.height_sources.remove(source)
                    
            # Remove any active issues that match up with the removed sensors.
            for issue in self.active_issues:
                if issue.id == self.controller_id and issue.sub_id == sensor.sensor_id:
                    issue.expire(force_expire=True)

    def handle_request_sensor(self, manager, sensor_id):
        
        sensor = self.find_sensor(sensor_id)
        
        manager.send_message('entire_sensor_update', sensor.public_info)
        
    def handle_change_sensor_setting(self, manager, sensor_id, change):

        sensor = self.find_sensor(sensor_id)
        
        setting_name, new_value = change
        
        # Check if setting is allowed to change once driver is up and running.
        has_changeable_tag = False
        for sensor_setting in sensor.metadata['settings']:
            if sensor_setting['name'] == setting_name:
                if 'changeable' in sensor_setting.get('tags',[]):
                    has_changeable_tag = True
                    break
  
        # Make sure value is allowed to be changed.
        # KLM - disabled check on session active since it's convenient to be able to change a setting at the beginning of a session
        # if something isn't setup right.  
        value_can_change = True
        #if self.session.active:
        #    self.log_message('Cannot change setting while session is active.', logging.ERROR, manager)
        #    value_can_change = False
        if not sensor.is_closed() and not has_changeable_tag:
            self.log_message('Cannot change setting until sensor is closed.', logging.ERROR, manager)
            value_can_change = False
        
        if not value_can_change:
            manager.send_message('entire_sensor_update', sensor.public_info) # so user can be notified setting didn't change.
            return 
        
        try:
            new_value = make_unicode(new_value).strip()
            sensor.update_setting(setting_name, new_value)
        except ValueError as e:
            self.log_message(make_unicode(e), logging.ERROR, manager)
            manager.send_message('entire_sensor_update', sensor.public_info) # so user can be notified setting didn't change.
        except KeyError:
            self.log_message("Can't change sensor setting {} because it does not exist.".format(setting_name), logging.ERROR, manager)
            manager.send_message('entire_sensor_update', sensor.public_info) # so user can be notified setting didn't change.
        
    def handle_change_sensor_info(self, manager, sensor_id, change):

        sensor = self.find_sensor(sensor_id)
        
        # Make sure value is allowed to be changed.
        value_can_change = True
        if self.session.active:
            self.log_message('Cannot change info while session is active.', logging.ERROR, manager)
            value_can_change = False
        elif not sensor.is_closed():
            self.log_message('Cannot change info until sensor is closed.', logging.ERROR, manager)
            value_can_change = False
        
        if not value_can_change:
            manager.send_message('entire_sensor_update', sensor.public_info) # so user can be notified setting didn't change.
            return 
        
        info_name, value = change
        
        try:
            value = value.strip()
        except AttributeError:
            pass
        
        if info_name == 'instrument_tag':
            value = format_id(make_unicode(value))
            if value != '':
                sensor.instrument_tag = value
            else:
                self.log_message("Instrument tag can't be empty.", logging.ERROR, manager)
                manager.send_message('entire_sensor_update', sensor.public_info) # so user can be notified setting didn't change.
            
        elif info_name == 'position_offsets':
            try:
                sensor.position_offsets = value
            except ValueError:
                self.log_message('Invalid position offset.', logging.ERROR, manager)
                manager.send_message('entire_sensor_update', sensor.public_info) # so user can be notified setting didn't change.
        elif info_name == 'orientation_offsets':
            try:
                sensor.orientation_offsets = value
            except ValueError:
                self.log_message('Invalid orientation offset.', logging.ERROR, manager)
                manager.send_message('entire_sensor_update', sensor.public_info) # so user can be notified setting didn't change.
        else:
            self.log_message("The info {} cannot be changed externally.".format(info_name), logging.ERROR, manager)
            manager.send_message('entire_sensor_update', sensor.public_info) # so user can be notified setting didn't change.
            
    def handle_send_sensor_command(self, manager, sensor_id, command):

        command_name, command_args = command

        if sensor_id == 'all':
            sensors = self.sensors
        else:
            sensors = [self.find_sensor(sensor_id)]

        for sensor in sensors:
            if command_name == 'close':
                self.close_down_sensor(sensor)
            else:
                sensor.send_command(command_name, command_args)
    
    def handle_change_controller_info(self, manager, info_name, info_value):

        # Make sure data source is allowed to be changed.
        if self.session.active:
            self.log_message('Cannot change info while session is active.', logging.ERROR, manager)
            self.send_entire_controller_info() # so user can be notified didn't change.
            return 
        
        try:
            info_value = info_value.strip()
        except AttributeError:
            pass

        if info_name == 'time_source':
            self.time_source = info_value
        elif info_name == 'position_sources':
            self.position_sources = info_value
        elif info_name == 'orientation_sources':
            self.orientation_sources = info_value
        elif info_name == 'height_sources':
            self.height_sources = info_value
        elif info_name == 'fixed_height_source':
            self.fixed_height_source = info_value
        else:
            self.log_message("Info '{}' cannot be changed externally.".format(info_name), logging.ERROR, manager)

    def handle_change_controller_setting(self, manager, setting_name, setting_value):

        # Make sure value is allowed to be changed.
        value_can_change = True
        if self.session.active:
            if setting_name == 'base_out_directory':
                self.log_message('Cannot change output directory while session is active.', logging.ERROR, manager)
                value_can_change = False
            if setting_name in ['platform_type', 'platform_tag']:
                self.log_message('Cannot change platform type/tag while session is active. If you need to you must manually rename session '
                                 'output folder AND change value in session_info.csv after session has ended.', logging.ERROR, manager)
                value_can_change = False
        elif not setting_name in self.settings:
            self.log_message('Cannot change setting {} because that settings does not exist.'.format(setting_name), logging.ERROR, manager)
            value_can_change = False
        
        if not value_can_change:
            self.send_entire_controller_info() # so user can be notified setting didn't change.
            return 
        
        try:
            settings_value = setting_name.strip()
        except AttributeError:
            pass
        
        self.update_controller_setting(setting_name, setting_value, manager)

    def update_controller_setting(self, setting_name, setting_value, manager=None):
        
        try:
            setting_type = self.setting_name_to_type[setting_name]
            
            try:
                setting_value = validate_type(setting_value, setting_type)
            except ValueError:
                self.log_message("{} cannot be converted into the expected type '{}'".format(setting_value, setting_type), logging.ERROR, manager)
                self.send_entire_controller_info() # so user can be notified setting didn't change.
                return # don't set value

        except KeyError:
            pass # setting doesn't have type so can't validate it, just set it below
        
        if setting_name not in self.settings:
            self.log_message("Can't add new controller setting {}".format(setting_name), logging.ERROR, manager)
            self.send_entire_controller_info() # so user can be notified setting didn't take effect.
            return # don't add new setting
        
        self.settings[setting_name] = setting_value
        self.send_entire_controller_info() # so user can be notified setting changed 

    def handle_setup_sensor(self, manager, sensor_id, message_body):
        
        if sensor_id == 'all':
            if len(self.sensors) == 0:
                self.log_message('No sensors loaded.', logging.ERROR, manager)
                return

            for sensor in self.sensors:
                sensor.setup()
        else:
            # Just want to setup a single sensor
            try:
                sensor = self.find_sensor(sensor_id)
                sensor.setup()
            except ValueError:
                self.log_message('Cannot setup sensor {} since it does not exist'.format(sensor_id), logging.ERROR, manager)

    def handle_new_sensor_data(self, sensor, utc_time, sys_time, data, data_ok):
        
        # TODO manage manager subscriptions
        # TODO only send to other controllers if not paused
        self.manager_interface.send_message_to_all('new_sensor_data', (sensor.sensor_id, utc_time, sys_time, data, data_ok))
        
        if not data_ok:
            # Assume data cant be used (ie time information, etc)
            return 
        
        # Now that we know data is ok determine if the sensor is any of our data sources.
        # TODO - make this more efficient.
        is_time_source = self.time_source and self.time_source.matches(sensor.sensor_id, self.controller_id)
        matching_position_sources = [source for source in self.position_sources if source.matches(sensor.sensor_id, self.controller_id)]
        matching_orientation_sources = [source for source in self.orientation_sources if source.matches(sensor.sensor_id, self.controller_id)]
        matching_height_sources = [source for source in self.height_sources if source.matches(sensor.sensor_id, self.controller_id)]
        
        if is_time_source:
            self.time_source.mark_updated()
            self.process_time_source_data(utc_time, sys_time)
        
        for source in matching_position_sources:
            source.mark_updated()
            self.process_position_source_data(source, utc_time, sys_time, data)
        
        for source in matching_orientation_sources:
            source.mark_updated()
            self.process_orientation_source_data(source, utc_time, sys_time, data)

        for source in matching_height_sources:
            source.mark_updated()
            self.process_height_source_data(source, utc_time, sys_time, data)

        # Check if we should log data. This assumes that data is ok.
        need_to_log_data = (not sensor.sensor_paused) and self.session.state == 'started'

        if need_to_log_data:
            # Write data to corresponding sensor log.
            data.insert(0, utc_time)
            sensor.output_file.write(data)
            
    def handle_data_source_data(self, manager, sensor_id, controller_id, data):

        raise NotImplementedError()
        #self.try_process_data_source_data(sensor_id, controller_id, data)

    def process_time_source_data(self, utc_time, sys_time):

        if sys_time <= 0:
            # Time came from another controller so timestamp when we received it to account for future latency.
            sys_time = time.time()
            
        new_time = (utc_time, sys_time)
        for sensor in self.sensors:
            sensor.send_time(new_time)

        self.last_utc_time = utc_time
        self.last_sys_time_update = time.time()
        
    def process_position_source_data(self, source, utc_time, sys_time, data):

        x = data[source.position_x_idx]
        y = data[source.position_y_idx]
        z = data[source.position_z_idx]
        position_data = [x, y, z]

        # TODO just send to local manager.
        self.manager_interface.send_message_to_all('new_source_data', (source.sensor_id, 'position', utc_time, sys_time, position_data))
                    
    def process_orientation_source_data(self, source, utc_time, sys_time, data):

        angle = data[source.orientation_idx]
        orientation_data = [source.angle_name[0], angle]
        
        # TODO just send to local manager.
        self.manager_interface.send_message_to_all('new_source_data', (source.sensor_id, 'orientation', utc_time, sys_time, orientation_data))
            
    def process_height_source_data(self, source, utc_time, sys_time, data):

        height_data = data[source.height_idx]

        # TODO just send to local manager.
        self.manager_interface.send_message_to_all('new_source_data', (source.sensor_id, 'height', utc_time, sys_time, height_data))

    def handle_controller_command(self, manager, command_name, command_args):
        
        if command_name == 'start_session':
            self.session.begin_startup_procedure(manager)
        elif command_name == 'pause_session':
            if self.session.active:
                self.session.state = 'paused'
                self.log_message('Session paused.', logging.INFO)
                
            # Set flag so if session is (or will be) suspended that session won't automatically resume when issues are resolved.
            self.session.pause_on_resume = True
                
            # Make sure sensors aren't saving data files.
            self.send_command_to_all_sensors('pause')
            
        elif command_name == 'stop_session':
            self.session.notes = command_args
            self.stop_session(manager)
        elif command_name == 'invalidate_session':
            if not self.session.active:
                self.log_message("Can't invalidate session because there isn't one active.")
                return
            self.log_message("Session invalidated.")
            self.session.invalidated = True
        else:
            self.log_message("Controller command {} not supported".format(command_name), logging.ERROR, manager)

    def handle_new_sensor_text(self, sensor, text):
        
        self.manager_interface.send_message_to_all('new_sensor_text', (sensor.sensor_id, text))
        sensor.text_messages.append(text)
    
    def handle_new_sensor_status(self, sensor, state, health, paused):

        sensor.sensor_state = state
        sensor.sensor_health = health
        sensor.sensor_paused = paused
        
    def handle_new_sensor_heartbeat(self, sensor, unused):
        # Don't need to do anything since all sensor messages are treated as heartbeats.
        pass
    
    def handle_new_sensor_event(self, sensor, event_name, event_args):
            
        if event_name == 'closing':
            sensor.update_connection_state('closed')
        if event_name == 'time_test':
            start_time = event_args
            duration = time.time() - start_time
            self.time_test_durations.append(duration)
            if len(self.time_test_durations) == 100:
                avg_dur = float(sum(self.time_test_durations)) / max(len(self.time_test_durations), 1)
                max_dur = max(self.time_test_durations)
                min_dur = min(self.time_test_durations)
                self.handle_new_sensor_text(sensor, "Avg {} Max {} Min {}".format(avg_dur, max_dur, min_dur))
                self.time_test_durations = []
        
    def notify_sensor_changed(self, sensor_id, info_name, value):
        self.manager_interface.send_message_to_all('sensor_changed', (sensor_id, info_name, value))
        
    def notify_session_changed(self, info_name, value):
        # TODO just send the info that changed...
        self.send_entire_controller_info()
        
        if info_name == 'active':
            if value == True:
                self.send_session_event('started')
            else:
                self.send_session_event('ended')
                    
    def verify_controller_settings(self, manager):
        
        # Need to make sure settings are valid before starting a session.
        empty_setting_names = []
        for key, value in self.settings.iteritems():
            if value is None or (isinstance(value, basestring) and value.strip() == ''):
                empty_setting_names.append(key)
        if len(empty_setting_names) > 0:
            formatted_setting_names = ''.join(['\n   - ' + name for name in empty_setting_names])
            self.log_message("Can't start session until the following settings are updated:{}".format(formatted_setting_names), logging.ERROR, manager)
            return False
        
        # Make sure output directory exists.
        if not os.path.exists(self.settings['base_out_directory']):
            self.log_message("Can't start session because the output directory doesn't exist.", logging.ERROR, manager)
            return False
        
        return True # all settings valid

    def send_command_to_all_sensors(self, command_name, command_args=None):
        
        for sensor in self.sensors:
            sensor.send_command(command_name, command_args)

    def stop_session(self, manager, interrupted=False):
        
        self.stopping_session = True
        self.session.stop(interrupted)
        self.stopping_session = False

    def write_session_file(self):
        
        file_path = os.path.join(self.session.path, 'session_info.csv')
        with open(file_path, 'wb') as outfile:
            writer = csv.writer(outfile)
            
            writer.writerow(utf_8_encoder(['start_utc', self.session.start_utc]))
            formatted_start_time = datetime.datetime.fromtimestamp(self.session.start_utc).strftime("%Y/%m/%d %H:%M:%S")
            writer.writerow(utf_8_encoder(['start_utc_human', formatted_start_time]))
            
            writer.writerow(utf_8_encoder(['end_utc', self.last_utc_time]))
            formatted_end_time = datetime.datetime.fromtimestamp(self.last_utc_time).strftime("%Y/%m/%d %H:%M:%S")
            writer.writerow(utf_8_encoder(['end_utc_human', formatted_end_time]))
            
            writer.writerow(utf_8_encoder(['start_sys_time', self.session.start_sys_time]))
            writer.writerow(utf_8_encoder(['end_sys_time', self.last_sys_time_update]))
            
            writer.writerow(utf_8_encoder(['controller_id', self.controller_id]))
            writer.writerow(utf_8_encoder(['app_version', app_version]))
            writer.writerow(utf_8_encoder(['output_version', output_version]))
            #writer.writerow(utf_8_encoder(['utc_difference', self.session.start_utc - self.session.start_sys_time]))
            
            for key, value in sorted(self.settings.items()):
                writer.writerow(utf_8_encoder([key, value]))
                
            if self.session.notes is not None:
                writer.writerow(utf_8_encoder(['notes', self.session.notes]))
                    
    def write_offsets_file(self):
        
        file_path = os.path.join(self.session.path, 'sensor_offsets.csv')
        with open(file_path, 'wb') as outfile:
            writer = csv.writer(outfile)
            
            writer.writerow(utf_8_encoder(['#sensor_name', 'sensor_type', 'sensor_tag', 'x', 'y', 'z', 'roll', 'pitch', 'yaw']))
            for sensor in self.sensors:
                writer.writerow(utf_8_encoder([sensor.sensor_id, sensor.instrument_type, sensor.instrument_tag] +
                                               sensor.position_offsets + sensor.orientation_offsets))

    def write_sensor_info_files(self):
        
        info_directory = os.path.join(self.session.path, 'sensor_info/')
        
        if not os.path.exists(info_directory):
            os.makedirs(info_directory)
        
        for sensor in self.sensors:
            
            file_path = os.path.join(info_directory, '{}_{}_{}.yaml'.format(sensor.sensor_id, sensor.instrument_type, sensor.instrument_tag))
            
            with open(file_path, 'w') as outfile:
                outdata = {}
                for key, value in sensor.public_info.items():
                    if key in ['sensor_type', 'sensor_id', 'controller_id', 'settings', 'parameters', 'text_messages',
                                'position_offsets', 'orientation_offsets', 'instrument_type', 'instrument_tag', 'metadata']:
                        outdata[key] = value
                outfile.write(yaml.safe_dump(outdata, allow_unicode=True, default_flow_style=False))

    def write_data_source_info_files(self):
        
        info_file_path = os.path.join(self.session.path, 'source_info.yaml')
        
        outdata = {}

        if self.time_source is not None:
            saved_info = {}
            saved_info['sensor_id'] = self.time_source.sensor_id
            saved_info['controller_id'] = self.time_source.controller_id
            # Don't need to specify time index since it's standardized as first piece of data.
            outdata['time_source'] = saved_info
            
        outdata['position_sources'] = []
        for position_source in self.position_sources:
            saved_info = {}
            saved_info['sensor_id'] = position_source.sensor_id
            saved_info['controller_id'] = position_source.controller_id
            saved_info['x_index'] = position_source.position_x_idx
            saved_info['y_index'] = position_source.position_y_idx
            saved_info['z_index'] = position_source.position_z_idx
            
            outdata['position_sources'].append(saved_info)    
            
        for orientation_source in self.orientation_sources:
            saved_info = {}
            saved_info['sensor_id'] = orientation_source.sensor_id
            saved_info['controller_id'] = orientation_source.controller_id
            saved_info['orientation_index'] = orientation_source.orientation_idx
            
            source_name = orientation_source.angle_name + '_source'
            outdata[source_name] = saved_info
            
        outdata['height_sources'] = []
        for height_source in self.height_sources:
            saved_info = {}
            saved_info['sensor_id'] = height_source.sensor_id
            saved_info['controller_id'] = height_source.controller_id
            saved_info['height_index'] = height_source.height_idx

            outdata['height_sources'].append(saved_info)
            
        if self.fixed_height_source is not None:
            saved_info = {}
            saved_info['height'] = self.fixed_height_source
            
            outdata['fixed_height_source'] = saved_info
        
        with open(info_file_path, 'w') as outfile:
            outfile.write(yaml.safe_dump(outdata, allow_unicode=True, default_flow_style=False))

    def find_sensor(self, sensor_id):
        
        for sensor in self.sensors:
            if sensor.sensor_id == sensor_id:
                return sensor
            
        raise ValueError("Sensor {} not in list of sensor IDs {}".format(sensor_id, [s.sensor_id for s in self.sensors]))
    
    def try_create_issue(self, main_id, sub_id, issue_type, reason, level):
        
        # First see if we need to promote the level to critical if this is a data source. 
        # Need to do this before constructing 'sensor_info' below.
        for data_source in [self.time_source] + self.position_sources + self.orientation_sources + self.height_sources:
            if data_source and data_source.matches(sensor_id=sub_id, controller_id=main_id):
                level = 'critical'
                break
        
        issue_info = {'id': main_id, 'sub_id': sub_id, 'type': issue_type, 'reason': reason, 'level': level}
        
        existing_issue = None
        for issue in self.active_issues:
            if issue.matches(issue_info):
                existing_issue = issue
                break
            
        if existing_issue:
            existing_issue.renew()
            if reason != existing_issue.reason:
                existing_issue.reason = reason
                self.send_controller_issue_event('issue_changed', existing_issue)
                self.send_entire_controller_info()
            if level != existing_issue.level:
                existing_issue.level = level
                self.send_controller_issue_event('issue_changed', existing_issue)
                self.send_entire_controller_info()
        else:
            new_issue = Issue(**issue_info)
            self.active_issues.append(new_issue)
            self.send_controller_issue_event('new_active_issue', new_issue)
            self.send_entire_controller_info()
    
    def try_resolve_issue(self, sub_id, issue_type):
        
        issue_info = {'id': self.controller_id, 'sub_id': sub_id, 'type': issue_type}
        
        for issue in self.active_issues:
            if issue.matches(issue_info):
                issue.expire()
                break

    def _make_sensor_name_unique(self, sensor_name, sensor_id='none'):
        
        existing_sensor_names = [s.sensor_id for s in self.sensors if s.sensor_id != sensor_id]
        original_sensor_name = sensor_name
        
        while sensor_name in existing_sensor_names:
            try:
                name_parts = sensor_name.split('-')
                i = int(name_parts[-1])
                i += 1
                sensor_name = '-'.join(name_parts[:-1] + [make_unicode(i)])
            except (ValueError, IndexError):
                sensor_name = '{}-{}'.format(original_sensor_name, 1)
                
        return sensor_name
    
