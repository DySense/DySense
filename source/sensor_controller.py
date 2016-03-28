#!/usr/bin/env python

import os
import time
import zmq
import json
import threading
import uuid
import datetime
import sys
import logging
import csv
import yaml
from logging import getLogger

from sensor_connection import SensorConnection
from sensor_creation import SensorDriverFactory, SensorCloseTimeout
from csv_log import CSVLog
from controller_data_sources import *

SENSOR_HEARTBEAT_PERIOD = 0.5 # how long to wait between sending/expecting heartbeats from sensors (in seconds)

class ManagerConnection(object):
    
    def __init__(self, router_id, is_on_different_computer):

        self.id = router_id
        self.is_on_different_computer = is_on_different_computer

class SensorController(object):
    
    def __init__(self, context, metadata):
        
        self.setup_logging()
        
        self.context = context
        
        self.version = metadata['version']
        self.sensor_metadata = metadata['sensors']
        
        self.sensors = []
        self.managers = {}
        
        self._session_active = False
        self._session_name = 'N/A'
        self.session_path = "None"
        
        self.text_messages = []
        
        self._time_source = None
        self._position_sources = []
        self._orientation_sources = []
        
        self.controller_id = str(uuid.uuid4())
        
        self.settings = {'base_out_directory': '',
                         'operator_name': '',
                         'platform_name': '',
                         'platform_id': '',
                         'field_id': '',
                         'surveyed': True}
        
        # Vehicle position/orientation files. New ones created for each session.
        self.position_source_log = None
        self.orientation_source_log = None

        # Start ID at 1 since 0 represents all sensors. Note IDs are always stored as strings.. not integers.
        self.next_sensor_id = 1
        
        self.stop_request = threading.Event()
        
        self._session_state = 'closed'
        
        # Last utc time received from timesource.  Set to None when a session is stopped.
        self.first_received_utc_time = None
        
        # Similar to first received utc time, but doesn't get invalided after session is stopped.
        self.session_start_utc = 0.0
        
        # Last received utc time.
        self.last_utc_time = 0.0
        
        # Used for creating new sensor drivers. Can't instantiate it until we know what endpoints we're bound to.
        self.sensor_driver_factory = None
        
        # Endpoints for sensors and managers to connect to.
        # Need to bind to all interfaces for managers since they can connect from another computer.
        self.sensor_local_endpoint = 'inproc://sensors'
        self.sensor_remote_endpoints = ['tcp://127.0.0.1:{}'.format(p) for p in range(60110, 60120)]
        self.manager_local_endpoint = 'inproc://managers'
        self.manager_remote_endpoints = ['tcp://0.0.0.0:{}'.format(p) for p in range(60120, 60130)]
        
        # ZMQ sockets aren't threadsafe so need to wait until thread starts to create them.
        self.manager_socket = None
        self.sensor_socket = None
        
        # Lookup tables of {client_id: router_id} so we can figure out how to address clients.
        self.sensor_router_ids = {}
        
        self.message_callbacks = { # From Managers
                                  'request_connect': self.handle_request_connect,
                                  'add_sensor': self.handle_add_sensor,
                                  'remove_sensor': self.handle_remove_sensor,
                                  'request_sensor': self.handle_request_sensor,
                                  'setup_sensor': self.handle_setup_sensor,
                                  'change_sensor_info': self.handle_change_sensor_info,
                                  'change_sensor_setting': self.handle_change_sensor_setting,
                                  'send_sensor_command': self.handle_send_sensor_command,
                                  'change_data_source': self.handle_change_data_source,
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
        
        # Time is treated as a double-precision floating point number which should always be true.
        # If for some reason it's not then notify a user that all times will be incorrect.
        max_required_precision = 1e-13
        if sys.float_info.epsilon > max_required_precision:
            raise Exception('System doesn\'t support required precision. Time\'s will not be correct.')

    @property
    def public_info(self):
        return {'id': self.controller_id,
                'version': self.version,
                'session_state': self.session_state,
                'session_active': self.session_active,
                'session_name': self.session_name,
                'time_source': None if not self.time_source else self.time_source.public_info,
                'position_sources': [source.public_info for source in self.position_sources],
                'orientation_sources': [source.public_info for source in self.orientation_sources],
                'settings': self.settings,
                'text_messages': self.text_messages}
        
    @property
    def session_state(self):
        return self._session_state
    @session_state.setter
    def session_state(self, new_value):
        self._session_state = new_value
        self.send_entire_controller_info()
        
    @property
    def session_active(self):
        return self._session_active
    @session_active.setter
    def session_active(self, new_value):
        self._session_active = new_value
        self.send_entire_controller_info()
        
    @property
    def session_name(self):
        return self._session_name
    @session_name.setter
    def session_name(self, new_value):
        self._session_name = new_value
        self.send_entire_controller_info()
        
    @property
    def time_source(self):
        return self._time_source
    @time_source.setter
    def time_source(self, new_value):
        if new_value is None:
            self._time_source = None
        else:
            self._time_source = TimeDataSource(callback=self.send_entire_controller_info,
                                               controller_id=new_value['controller_id'],
                                               sensor_id=new_value['sensor_id'],
                                               sensor_name=new_value['sensor_name'],
                                               sensor_metadata=new_value['metadata'])
        self.send_entire_controller_info()
        
    @property
    def position_sources(self):
        return self._position_sources
    @position_sources.setter
    def position_sources(self, new_value):
        self._position_sources = []
        for val in new_value:
            self._position_sources.append(PositionDataSource(callback=self.send_entire_controller_info,
                                                             controller_id=val['controller_id'],
                                                             sensor_id=val['sensor_id'],
                                                             sensor_name=val['sensor_name'],
                                                             sensor_metadata=val['metadata']))
        self.send_entire_controller_info()
        
    @property
    def orientation_sources(self):
        return self._orientation_sources
    @orientation_sources.setter
    def orientation_sources(self, new_value):
        self._orientation_sources = []
        for val in new_value:
            self._orientation_sources.append(OrientationDataSource(callback=self.send_entire_controller_info,
                                                                   controller_id=val['controller_id'],
                                                                   sensor_id=val['sensor_id'],
                                                                   sensor_name=val['sensor_name'],
                                                                   sensor_metadata=val['metadata']))
        self.send_entire_controller_info()
        
    def setup_logging(self):
        
        # Use home directory for root output directory. This is platform independent and works well with an installed package.
        home_directory = os.path.expanduser('~')
        output_directory = os.path.join(home_directory, 'dysense_logs/')
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        
        # Create logger to write out to a file.
        log = logging.getLogger("dysense")
        handler = logging.FileHandler(os.path.join(output_directory, time.strftime("%Y-%m-%d_%H-%M-%S_dysense_log.log")))
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s'))
        log.addHandler(handler)
        
    def setup_session_logging(self, output_directory):

        # Create logger to write out to a file.
        log = logging.getLogger("session")
        handler = logging.FileHandler(os.path.join(output_directory, time.strftime("session_log.log")))
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s'))
        log.addHandler(handler)
    
    def close_session_logging(self):
        
        session_log = getLogger('session')
        handlers = session_log.handlers[:]
        for handler in handlers:
            handler.close()
            session_log.removeHandler(handler)
        
    def log_message(self, msg, level=logging.INFO, manager=None):
        
        getLogger('dysense').log(level, msg)
        
        if self.session_active:
            getLogger('session').log(level, msg)
        
        if manager is not None and level >= logging.ERROR:
            self._send_manager_message(manager.id, 'error_message', (msg, level))
            
        self.text_messages.append(msg)
        self._send_manager_message('all', 'new_controller_text', msg)
        
    def run(self):
        # TODO - report unhandled exceptions http://stackoverflow.com/questions/22581496/error-in-pyqt-qthread-not-printed
        try:
            self.setup()
            self.run_message_loop()
        finally:
            self.close_down()

    def setup(self):
        
        self.manager_socket = self.context.socket(zmq.ROUTER)
        self.sensor_socket = self.context.socket(zmq.ROUTER)
        
        self.manager_socket.bind(self.manager_local_endpoint)
        self.bind_to_first_open_endpoint(self.manager_socket, self.manager_remote_endpoints)
        self.sensor_socket.bind(self.sensor_local_endpoint)
        self.sensor_remote_endpoint = self.bind_to_first_open_endpoint(self.sensor_socket, self.sensor_remote_endpoints)

        self.sensor_driver_factory = SensorDriverFactory(self.context, self.sensor_local_endpoint, self.sensor_remote_endpoint)

    def run_message_loop(self):
    
        # Use a poller so we can use timeout to check if any sensors aren't responding.
        timeout = SENSOR_HEARTBEAT_PERIOD * 1000  # milliseconds
        poller = zmq.Poller()
        poller.register(self.manager_socket, zmq.POLLIN)
        poller.register(self.sensor_socket, zmq.POLLIN)
    
        while True:
            
            if self.stop_request.is_set():
                break  # from main loop
            
            self.process_new_messages(poller, timeout)

            # TODO only do this at a certain rate
            for sensor in self.sensors:
                # Mark that we've tried to receive message from sensor.
                sensor.last_message_processing_time = time.time()
                
                if sensor.stopped_responding() and not sensor.closing:
                    sensor.update_connection_state('timed_out')
                else:
                    if sensor.need_to_send_heartbeat():
                        self._send_sensor_message(sensor.sensor_id, 'heartbeat', '')
                        sensor.last_sent_heartbeat_time = time.time()
                    if sensor.num_messages_received > 0 and not sensor.closing:
                        sensor.update_connection_state('opened')
            
            # TODO only do this at a certain rate
            self.update_session_state()
            
    def close_down(self):
        
        self.log_message("Controller closing down.")
        
        for sensor in self.sensors:
            self.close_down_sensor(sensor)
            
        if self.manager_socket:
            self.manager_socket.close()
            
        if self.sensor_socket:
            self.sensor_socket.close()
            
    def close_down_sensor(self, sensor):
        
        self._send_sensor_message(sensor.sensor_id, 'command', 'close')
        try:
            sensor.close()
        except SensorCloseTimeout:
            pass  # TODO notify managers that sensor failed to close down.
            
    def process_new_messages(self, poller, timeout):

        msgs = dict(poller.poll(timeout)) 

        if self.sensor_socket in msgs and msgs[self.sensor_socket] == zmq.POLLIN:
            # New message is waiting.
            self.process_new_message_from_sensor()
            
        if self.manager_socket in msgs and msgs[self.manager_socket] == zmq.POLLIN:
            # New message is waiting.
            self.process_new_message_from_manager()
            
    def process_new_message_from_sensor(self):
        
        router_id, message = self.sensor_socket.recv_multipart()
        message = json.loads(message)
        sensor_id = str(message['sensor_id'])
        self.sensor_router_ids[sensor_id] = router_id 
        try:
            sensor = self.find_sensor(sensor_id)
        except ValueError:
            print "Couldn't handle message from sensor {} since it doesn't exist.".format(sensor_id)
            return
        
        message_callback = self.message_callbacks[message['type']]
        message_body = message['body']
        if isinstance(message_body, (tuple, list)):
            message_callback(sensor, *message_body)
        else:
            message_callback(sensor, message_body)
            
        sensor.last_received_message_time = time.time()
        sensor.last_message_processing_time = time.time()
        sensor.num_messages_received += 1
        
    def process_new_message_from_manager(self):
        
        router_id, message = self.manager_socket.recv_multipart()
        message = json.loads(message)
        
        if router_id not in self.managers:
            self.managers[router_id] = ManagerConnection(router_id, False)

        manager = self.managers[router_id]
        message_callback = self.message_callbacks[message['type']]
        message_body = message['body']
        if isinstance(message_body, (tuple, list)):
            message_callback(manager, *message_body)
        else:
            message_callback(manager, message_body)
        
    def bind_to_first_open_endpoint(self, socket, endpoints):
        
        for endpoint in endpoints:
            try:
                socket.bind(endpoint)
                return endpoint
            except (zmq.ZMQBindError, zmq.ZMQError):
                continue  # Try next endpoint
  
        raise Exception("Failed to bind to any of the following endpoints {}".format(endpoints))
        
    def send_entire_controller_info(self):
    
        self._send_manager_message('all', 'entire_controller_update', self.public_info)
        
    def send_entire_sensor_info(self, manager_id, sensor):
    
        self._send_manager_message(manager_id, 'entire_sensor_update', sensor.public_info)
        
    def handle_request_connect(self, manager, unused):
        
        self.send_entire_controller_info()
        
        for sensor in self.sensors:
            self.send_entire_sensor_info(manager.id, sensor)
        
    def handle_add_sensor(self, manager, sensor_info):
        '''Validate that sensor name is unique and adds to list of sensors.'''

        if self.session_active:
            self.log_message('Cannot add sensor while session is active.', logging.ERROR, manager)
            return
        
        if sensor_info['sensor_type'] not in self.sensor_metadata:
            self.log_message('Cannot add sensor with type {} because it does not exist in metadata.'.format(sensor_info['sensor_type']), logging.ERROR, manager)
            return
        
        # Get metadata that was stored with this controller.
        metadata = self.sensor_metadata[sensor_info['sensor_type']]
        
        sensor_name = sensor_info['sensor_name']
        sensor_type = sensor_info['sensor_type']
        position_offsets = sensor_info.get('position_offsets', [0, 0, 0])
        orientation_offsets = sensor_info.get('orientation_offsets', [0, 0, 0])
        instrument_id = sensor_info.get('instrument_id', 'none')
        
        settings = {}
        for setting_metadata in metadata['settings']:
            setting_name = setting_metadata['name']
            try:
                settings_value = sensor_info['settings'][setting_name]
            except KeyError:
                # User didn't provide this setting so try to use the default value.
                try:
                    settings_value = setting_metadata['default_value']
                except KeyError:
                    settings_value = None
        
            settings[setting_name] = settings_value 
        
        sensor_name = self._make_sensor_name_unique(sensor_name)
        
        new_sensor = SensorConnection(metadata['version'], str(self.next_sensor_id), sensor_type, sensor_name,
                                      SENSOR_HEARTBEAT_PERIOD, settings, position_offsets, orientation_offsets,
                                      instrument_id, metadata, self, self.sensor_driver_factory)
        
        self.next_sensor_id += 1
    
        self.sensors.append(new_sensor)
        
        self.send_entire_sensor_info('all', new_sensor)
        
        # Validate all settings once sensor has been sent to all managers.
        for setting_name, setting_value in new_sensor.settings.items():
            new_sensor.update_setting(setting_name, setting_value)
        
        self.log_message("Added new {} sensor.".format(sensor_type))
        
        # TODO - remove this once user can select data sources.  Right now if it can be a datasource then make it one.
        new_source_info =  {'controller_id': self.controller_id, 
                            'sensor_id': new_sensor.sensor_id,
                            'sensor_name': new_sensor.sensor_name, 
                            'metadata': new_sensor.metadata,  }
        if 'time' in metadata.get('tags',[]):
            self.time_source = new_source_info
        if 'position' in metadata.get('tags',[]):
            existing_source_info = []
            for existing_source in self.position_sources:
                existing_info =  {'controller_id': existing_source.controller_id, 
                                 'sensor_id': existing_source.sensor_id,
                                 'sensor_name': existing_source.sensor_name, 
                                 'metadata': existing_source.sensor_metadata,  }
                existing_source_info.append(existing_info)
            self.position_sources = existing_source_info + [new_source_info]
        if 'orientation' in metadata.get('tags',[]):
            self.orientation_sources = self.orientation_sources + [new_source_info]

    def handle_remove_sensor(self, manager, sensor_id):
        '''Search through sensors and remove one that has matching id.'''
        
        if self.session_active:
            self.log_message('Cannot remove sensor while session is active.', logging.ERROR, manager)
            return 
        
        if sensor_id == 'all':
            sensors = self.sensors
        else:
            sensors = [self.find_sensor(sensor_id)]
        
        for sensor in sensors[:]:
            self.close_down_sensor(sensor)
            self.sensors.remove(sensor)
            self._send_manager_message('all', 'sensor_removed', sensor.sensor_id)
            
            self.log_message("Removed {}".format(sensor.sensor_name))
            
            if self.time_source and self.time_source.matches(sensor.sensor_id, self.controller_id):
                self.time_source = None
            for source in self.position_sources[:]:
                if source.matches(sensor.sensor_id, self.controller_id):
                    self.position_sources.remove(source)
            for source in self.orientation_sources[:]:
                if source.matches(sensor.sensor_id, self.controller_id):
                    self.orientation_sources.remove(source)

    def handle_request_sensor(self, manager, sensor_id):
        
        sensor = self.find_sensor(sensor_id)
        
        self.send_entire_sensor_info(manager.id, sensor)
        
    def handle_change_sensor_setting(self, manager, sensor_id, change):

        sensor = self.find_sensor(sensor_id)
        
        # Make sure value is allowed to be changed.
        value_can_change = True
        if self.session_active:
            self.log_message('Cannot change setting while session is active.', logging.ERROR, manager)
            value_can_change = False
        elif not sensor.is_closed():
            self.log_message('Cannot change setting until sensor is closed.', logging.ERROR, manager)
            value_can_change = False
        
        if not value_can_change:
            self.send_entire_sensor_info(manager.id, sensor) # so user can be notified setting didn't change.
            return 
        
        setting_name, new_value = change

        try:
            new_value = str(new_value).strip()
            sensor.update_setting(setting_name, new_value)
        except ValueError as e:
            self.log_message(str(e), logging.ERROR, manager)
            self.send_entire_sensor_info(manager.id, sensor) # so user can be notified setting didn't change.
        except KeyError:
            self.log_message("Can't change sensor setting {} because it does not exist.".format(setting_name), logging.ERROR, manager)
            self.send_entire_sensor_info(manager.id, sensor) # so user can be notified setting didn't change.
        
    def handle_change_sensor_info(self, manager, sensor_id, change):

        sensor = self.find_sensor(sensor_id)
        
        # Make sure value is allowed to be changed.
        value_can_change = True
        if self.session_active:
            self.log_message('Cannot change info while session is active.', logging.ERROR, manager)
            value_can_change = False
        elif not sensor.is_closed():
            self.log_message('Cannot change info until sensor is closed.', logging.ERROR, manager)
            value_can_change = False
        
        if not value_can_change:
            self.send_entire_sensor_info(manager.id, sensor) # so user can be notified setting didn't change.
            return 
        
        info_name, value = change
        
        if info_name == 'sensor_name':
            new_name = self._make_sensor_name_unique(value.strip(), sensor_id)
            sensor.update_sensor_name(new_name)
        elif info_name == 'instrument_id':
            sensor.update_instrument_id(value)
        elif info_name == 'position_offsets':
            try:
                sensor.update_position_offsets(value)
            except ValueError:
                self.log_message('Invalid position offset.', logging.ERROR, manager)
                self.send_entire_sensor_info(manager.id, sensor) # so user can be notified setting didn't change.
        elif info_name == 'orientation_offsets':
            try:
                sensor.update_orientation_offsets(value)
            except ValueError:
                self.log_message('Invalid orientation offset.', logging.ERROR, manager)
                self.send_entire_sensor_info(manager.id, sensor) # so user can be notified setting didn't change.
        else:
            self.log_message("The info {} cannot be changed externally.".format(info_name), logging.ERROR, manager)
            self.send_entire_sensor_info(manager.id, sensor) # so user can be notified setting didn't change.
            
    def handle_send_sensor_command(self, manager, sensor_id, command):

        if sensor_id == 'all':
            sensors = self.sensors
        else:
            sensors = [self.find_sensor(sensor_id)]

        for sensor in sensors:
            if command == 'close':
                self.close_down_sensor(sensor)
            else:
                self._send_sensor_message(sensor.sensor_id, 'command', command)
    
    def handle_change_data_source(self, manager, data_source_name, data_source_info):

        # Make sure data source is allowed to be changed.
        if self.session_active:
            self.log_message('Cannot change source while session is active.', logging.ERROR, manager)
            self.send_entire_controller_info() # so user can be notified didn't change.
            return 

        data_source_info['receiving'] = False

        if data_source_name == 'time':
            self.time_source = data_source_info
        if data_source_name == 'position':
            self.position_source = data_source_info
        if data_source_name == 'orientation':
            self.orientation_source = data_source_info

    def handle_change_controller_setting(self, manager, settings_name, settings_value):

        # Make sure value is allowed to be changed.
        value_can_change = True
        if self.session_active:
            self.log_message('Cannot change controller settings while session is active.', logging.ERROR, manager)
            value_can_change = False
        elif not settings_name in self.settings:
            self.log_message('Cannot change setting {} because that settings does not exist.'.format(settings_name), logging.ERROR, manager)
            value_can_change = False
        
        if not value_can_change:
            self.send_entire_controller_info() # so user can be notified setting didn't change.
            return 

        self.settings[settings_name] = settings_value
        self.send_entire_controller_info()

    def handle_setup_sensor(self, manager, sensor_id, message_body):
        
        if sensor_id == 'all':
            sensors = self.sensors
        else:
            sensors = [self.find_sensor(sensor_id)]
        
        for sensor in sensors:
            sensor.setup()

    def handle_new_sensor_data(self, sensor, data):
        
        self.try_process_data_source_data(sensor.sensor_id, self.controller_id, data)

        if not self.session_active:
            return # TODO - need to update data sources 'receiving' even if we're not logging data.

        sensor.output_file.write(data)
        
        # TODO manage manager subscriptions 
        self._send_manager_message('all', 'new_sensor_data', (sensor.sensor_id, data))
    
    def handle_data_source_data(self, manager, sensor_id, controller_id, data):

        self.try_process_data_source_data(sensor_id, controller_id, data)

    def try_process_data_source_data(self, sensor_id, controller_id, data):
        
        if self.time_source and self.time_source.matches(sensor_id, controller_id):
            sys_time = data[self.time_source.sys_time_idx]
            if sys_time <= 0:
                # Time came from another controller so timestamp when we received it to account for future latency.
                sys_time = time.time()
                
            utc_time = data[self.time_source.utc_time_idx]

            new_time = (utc_time, sys_time)
            self._send_sensor_message('all', 'time', new_time)
            
            self.last_utc_time = utc_time
            
            # Save off utc time in case we need to use it for timestamping a new session.
            # Only grab the first one since the test GPS relies on that.
            if not self.first_received_utc_time:
                self.first_received_utc_time = utc_time
                self.session_start_utc = utc_time
            
        for source in self.position_sources:
            if source.matches(sensor_id, controller_id):
                utc_time = data[0]
                x = data[source.position_x_idx]
                y = data[source.position_y_idx]
                z = data[source.position_z_idx]
                position_data = [utc_time, x, y, z]
                if source.position_zone_idx is not None:
                    zone = data[source.position_zone_idx]
                    position_data.append(zone)
                    
                if len(self.position_sources) > 1:
                    position_data.insert(0, source.sensor_name)

                if self.session_active:
                    self.position_source_log.write(position_data)

        for source in self.orientation_sources:
            if source.matches(sensor_id, controller_id):
                pass #self.orientation_source_log.write((source.sensor_name,) + data)

    def handle_controller_command(self, manager, command_name):
        
        if command_name == 'start_session':
            self.begin_session_startup_procedure(manager)
        elif command_name == 'stop_session':
            self.stop_session(manager)
        else:
            self.log_message("Controller command {} not supported".format(command_name), logging.ERROR, manager)

    def handle_new_sensor_text(self, sensor, text):
        
        self._send_manager_message('all', 'new_sensor_text', (sensor.sensor_id, text))
        sensor.text_messages.append(text)
    
    def handle_new_sensor_status(self, sensor, state, health, paused):

        sensor.update_sensor_state(state)
        sensor.update_sensor_health(health)
        sensor.update_sensor_paused(paused)
        
    def handle_new_sensor_heartbeat(self, sensor, unused):
        # Don't need to do anything since all sensor messages are treated as heartbeats.
        pass
    
    def handle_new_sensor_event(self, sensor, event_name):
            
        if event_name == 'closing':
            sensor.closing = True
            sensor.update_connection_state('closed')
        
    def notify_sensor_changed(self, sensor_id, info_name, value):
        self._send_manager_message('all', 'sensor_changed', (sensor_id, info_name, value))
        
    def begin_session_startup_procedure(self, manager):
        
        if not self.verify_controller_settings(manager):
            return False
        
        if self.time_source is None:
            self.log_message("Can't start session without a selected time source.", logging.ERROR, manager)
            return
        
        # Make sure all sensors are setup and then that data sources are initially started. 
        for sensor in self.sensors:
            sensor.setup()

        time_sensor = self.find_sensor(self.time_source.sensor_id)
        position_sensors = [self.find_sensor(s.sensor_id) for s in self.position_sources]
        orientation_sensors = [self.find_sensor(s.sensor_id) for s in self.orientation_sources]
        
        for sensor in [time_sensor] + position_sensors + orientation_sensors:
            if sensor.num_messages_received == 0:
                self.log_message("Can't startup session until all data sources are setup.", logging.ERROR, manager)
                return False
            # Sensor is setup so can start it.
            self._send_sensor_message(sensor.sensor_id, 'command', 'resume')
            
        self.log_message("Initial startup successful.")
        self.session_state = 'waiting_for_time'
        
        return True # initial startup successful
        
    def update_session_state(self):
        
        if self.session_state == 'closed':
            return
        
        if self.session_state == 'waiting_for_time':
            if self.first_received_utc_time is not None:
                self.session_state = 'waiting_for_position'
        
        if self.session_state == 'waiting_for_position':
            for source in self.position_sources:
                if False: # TODO not source.receiving:
                    return
            # All sources receiving.    
            self.session_state = 'waiting_for_orientation'
        
        if self.session_state == 'waiting_for_orientation':
            for source in self.orientation_sources:
                if False: # TODO not source.receiving:
                    return
            # All sources receiving.    
            self.session_state = 'starting'
        
        if self.session_state == 'starting':
            self.start_session(self.first_received_utc_time)
            self.session_state = 'started'
            
        if self.session_state == 'started':
            pass # TODO monitor data sources and sensors and report events
        
        if self.session_state == 'suspended':
            pass # TODO monitor data sources nad sensors and see if can get back to started state

    def verify_controller_settings(self, manager):
        
        # Need to make sure settings are valid before starting a session.
        empty_setting_names = []
        for key, value in self.settings.iteritems():
            if value is None or (isinstance(value, str) and value.strip() == ''):
                empty_setting_names.append(key)
        if len(empty_setting_names) > 0:
            formatted_setting_names = ''.join(['\n   - ' + name for name in empty_setting_names])
            self.log_message("Can't start session until the following settings are updated:{}".format(formatted_setting_names), logging.ERROR, manager)
            return False
        
        return True # all settings valid
        
    def start_session(self, utc_time):
        
        formatted_time = datetime.datetime.fromtimestamp(utc_time).strftime("%Y%m%d_%H%M%S")
        
        self.session_name = "{}_{}_{}".format(self.settings['platform_name'],
                                              self.settings['platform_id'],
                                              formatted_time)
        
        self.session_path = os.path.join(self.settings['base_out_directory'], self.session_name)
        
        self.session_active = True
        
        self.log_message("Session started.")

        data_logs_path = os.path.join(self.session_path, 'data_logs/')
        
        if not os.path.exists(data_logs_path):
            os.makedirs(data_logs_path)
            
        self.setup_session_logging(self.session_path)

        for sensor in self.sensors:
            
            sensor_csv_file_name = "{}_{}_{}.csv".format(sensor.sensor_name,
                                                         sensor.instrument_id,
                                                         formatted_time)
            
            sensor_csv_file_path = os.path.join(data_logs_path, sensor_csv_file_name)
            
            sensor.output_file = CSVLog(sensor_csv_file_path, buffer_size=1)
            
        # Create vehicle state logs
        position_source_path = os.path.join(self.session_path, 'position.csv')
        self.position_source_log = CSVLog(position_source_path, 1)
        orientation_source_path = os.path.join(self.session_path, 'orientation.csv')
        self.orientation_source_log = CSVLog(orientation_source_path, 1)
            
        # Start all other sensors now that session is started.
        self.log_message("Starting all sensors.")
        for sensor in self.sensors:
            self._send_sensor_message(sensor.sensor_id, 'command', 'resume')

    def stop_session(self, manager):
        
        if not self.session_active:
            self.log_message("Session already closed.")
            return # already closed
        
        for sensor in self.sensors:
            self._send_sensor_message(sensor.sensor_id, 'command', 'pause')
        
        # Invalidate time-stamp so we don't use it again.
        self.first_received_utc_time = None
        
        self.position_source_log.terminate()
        self.orientation_source_log.terminate()
        self.position_source_log = None
        self.orientation_source_log = None
        
        self.close_session_logging()
        self.session_active = False
        self.session_state = 'closed'
        
        self.write_session_file()
        self.write_offsets_file()
        self.write_sensor_info_files()
        self.write_version_file()
        
        self.log_message("Session closed.")

    def write_session_file(self):
        
        file_path = os.path.join(self.session_path, 'session_info.csv')
        with open(file_path, 'wb') as outfile:
            writer = csv.writer(outfile)
            
            writer.writerow(['start_utc', self.session_start_utc])
            formatted_start_time = datetime.datetime.fromtimestamp(self.session_start_utc).strftime("%Y/%m/%d %H:%M:%S")
            writer.writerow(['start_utc_human', formatted_start_time])
            
            writer.writerow(['end_utc', self.last_utc_time])
            formatted_end_time = datetime.datetime.fromtimestamp(self.last_utc_time).strftime("%Y/%m/%d %H:%M:%S")
            writer.writerow(['end_utc_human', formatted_end_time])
            
            for key, value in sorted(self.settings.items()):
                if key not in ['base_out_directory']: 
                    writer.writerow([key, value])
                    
    def write_offsets_file(self):
        
        file_path = os.path.join(self.session_path, 'sensor_offsets.csv')
        with open(file_path, 'wb') as outfile:
            writer = csv.writer(outfile)
            
            writer.writerow(['#sensor_name', 'sensor_id', 'x', 'y', 'z', 'roll', 'pitch', 'yaw'])
            for sensor in self.sensors:
                writer.writerow([sensor.sensor_name, sensor.instrument_id] + sensor.position_offsets + sensor.orientation_offsets)

    def write_sensor_info_files(self):
        
        info_directory = os.path.join(self.session_path, 'sensor_info/')
        
        os.makedirs(info_directory)
        
        for sensor in self.sensors:
            
            file_path = os.path.join(info_directory, '{}_{}.yaml'.format(sensor.sensor_name, sensor.instrument_id))
            
            with open(file_path, 'w') as outfile:
                outdata = []
                for key, value in sorted(sensor.public_info.items()):
                    if key in ['sensor_type', 'sensor_name', 'settings', 'parameters', 'text_messages',
                                'position_offsets', 'orientation_offsets', 'instrument_id', 'metadata']:
                        outdata.append([key, value])
                outfile.write(yaml.dump(outdata, default_flow_style=False))

    def write_version_file(self):
        
        file_path = os.path.join(self.session_path, 'version.txt')
        with open(file_path, 'w') as outfile:
            outfile.write(self.version)

    def find_sensor(self, sensor_id):
        
        for sensor in self.sensors:
            if sensor.sensor_id == str(sensor_id):
                return sensor
            
        raise ValueError("Sensor {} not in list of sensor IDs {}".format(sensor_id, [s.sensor_id for s in self.sensors]))
    
    def _send_manager_message(self, manager_id, message_type, message_body):
        
        message = {'id': self.controller_id, 'type': message_type, 'body': message_body}
        
        if manager_id == 'all':  # send to all managers
            for router_id in self.managers.keys():
                self.manager_socket.send_multipart([router_id, json.dumps(message)])
        else:  # just send to a single manager
            router_id = manager_id
            self.manager_socket.send_multipart([router_id, json.dumps(message)])

    def _send_sensor_message(self, sensor_id, message_type, message_body):
        
        message = {'type': message_type, 'body': message_body}

        if sensor_id == 'all':  # send to all sensors
            for router_id in self.sensor_router_ids.values():
                self.sensor_socket.send_multipart([router_id, json.dumps(message)])
        else:  # just send to single sensor
            try:
                router_id = self.sensor_router_ids[sensor_id]
                self.sensor_socket.send_multipart([router_id, json.dumps(message)])
            except KeyError:
                pass  # haven't received message from sensor yet so don't know how to address it.

    def _make_sensor_name_unique(self, sensor_name, sensor_id='none'):
        
        existing_sensor_names = [s.sensor_name for s in self.sensors if s.sensor_id != sensor_id]
        original_sensor_name = sensor_name
        
        while sensor_name in existing_sensor_names:
            try:
                name_parts = sensor_name.split('_')
                i = int(name_parts[-1])
                i += 1
                sensor_name = '_'.join(name_parts[:-1] + [str(i)])
            except (ValueError, IndexError):
                sensor_name = '{}_{}'.format(original_sensor_name, 1)
                
        return sensor_name
    
