#!/usr/bin/env python

import time
import zmq
import json
import threading
import uuid

from sensor_connection import SensorConnection
from sensor_creation import SensorDriverFactory, SensorCloseTimeout

SENSOR_HEARTBEAT_PERIOD = 0.5 # how long to wait between sending/expecting heartbeats from sensors (in seconds)

class ManagerConnection(object):
    
    def __init__(self, router_id, is_on_different_computer):

        self.id = router_id
        self.is_on_different_computer = is_on_different_computer

class SensorController(object):
    
    def __init__(self, context, metadata):
        
        self.context = context
        
        self.version = metadata['version']
        self.sensor_metadata = metadata['sensors']
        
        self.sensors = []
        self.managers = {}
        
        self._session_active = False
        self._session_name = 'N/A'
        
        self.controller_id = str(uuid.uuid4())
        
        # Start ID at 1 since 0 represents all sensors.
        self.next_sensor_id = 1
        
        self.stop_request = threading.Event()
        
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
                                  'send_sensor_time': self.handle_send_sensor_time,
                                  
                                   # From Sensors
                                  'new_sensor_data': self.handle_new_sensor_data,
                                  'new_sensor_text': self.handle_new_sensor_text,
                                  'new_sensor_status': self.handle_new_sensor_status,
                                  'new_sensor_heartbeat': self.handle_new_sensor_heartbeat,
                                  }

    @property
    def public_info(self):
        return {'id': self.controller_id,
                'version': self.version,
                'session_active': self.session_active,
                'session_name': self.session_name}
        
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
        
    def run(self):

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
        timeout = SENSOR_HEARTBEAT_PERIOD * 1000 # milliseconds
        poller = zmq.Poller()
        poller.register(self.manager_socket, zmq.POLLIN)
        poller.register(self.sensor_socket, zmq.POLLIN)
    
        while True:
            
            if self.stop_request.is_set():
                break # from main loop
            
            self.process_new_messages(poller, timeout)

            for sensor in self.sensors:
                # Mark that we've tried to receive message from sensor.
                sensor.last_message_processing_time = time.time()
                
                if sensor.stopped_responding():
                    # TODO verify it should be 'timed_out'
                    sensor.update_connection_state('timed_out')
                else:
                    if sensor.need_to_send_heartbeat():
                        self._send_sensor_message(sensor.sensor_id, 'heartbeat', '')
                        sensor.last_sent_heartbeat_time = time.time()
            
    def close_down(self):
        
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
            pass # TODO notify managers that sensor failed to close down.
            
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
                continue # Try next endpoint
  
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
        
        if sensor_info['sensor_type'] not in self.sensor_metadata:
            # TODO return that sensor type doesn't even exist on this version.
            return
        
        # Get metadata that was stored with this controller.
        metadata = self.sensor_metadata[sensor_info['sensor_type']]
        
        if metadata['version'] != sensor_info['version']:
            # TODO return the sensor version doesn't match.
            return
        
        sensor_name = sensor_info['sensor_name']
        sensor_type = sensor_info['sensor_type']
        try:
            settings = sensor_info['settings']
        except KeyError:
            # Load default settings from metadata
            settings = {}
            try:
                for setting_metadata in metadata['settings']:
                    setting_name = setting_metadata.keys()[0]
                    try:
                        sensor_default_value = setting_metadata.values()[0]['default_value']
                    except KeyError:
                        sensor_default_value = None
                    settings[setting_name] = sensor_default_value 
            except KeyError:
                pass 
        
        sensor_name = self._make_sensor_name_unique(sensor_name)
        
        new_sensor = SensorConnection(metadata['version'], self.next_sensor_id, sensor_type, sensor_name,
                                      SENSOR_HEARTBEAT_PERIOD, settings, metadata, self, self.sensor_driver_factory)
        self.next_sensor_id += 1
    
        self.sensors.append(new_sensor)
        
        self.send_entire_sensor_info('all', new_sensor)

    def handle_remove_sensor(self, manager, sensor_id):
        '''Search through sensors and remove one that has matching id.'''
        
        sensor = self.find_sensor(sensor_id)
        
        self.close_down_sensor(sensor)
        self.sensors.remove(sensor)
        
        self._send_manager_message('all', 'sensor_removed', sensor_id)

    def handle_request_sensor(self, manager, sensor_id):
        
        sensor = self.find_sensor(sensor_id)
        
        self.send_entire_sensor_info(manager.id, sensor)
        
    def handle_change_sensor_setting(self, manager, sensor_id, change):
        
        sensor = self.find_sensor(sensor_id)
        
        setting_name, value = change
        sensor.update_setting(setting_name, value)
        
    def handle_change_sensor_info(self, manager, sensor_id, change):
        
        sensor = self.find_sensor(sensor_id)
        
        info_name, value = change
        
        if info_name == 'sensor_type':
            sensor.update_sensor_type(value)
        if info_name == 'sensor_name':
            sensor.update_sensor_name(value)
        
    def handle_send_sensor_command(self, manager, sensor_id, command):

        if command == 'close':
            self.close_down_sensor(self.find_sensor(sensor_id))
        else:
            self._send_sensor_message(sensor_id, 'command', command)
    
    def handle_send_sensor_time(self, manager, sensor_id, utc_time, sys_time):
        
        self._send_sensor_message(sensor_id, 'time', (utc_time, sys_time))

    def handle_setup_sensor(self, manager, sensor_id, message_body):
        
        if int(sensor_id) == 0:
            sensors = self.sensors
        else:
            sensors = [self.find_sensor(sensor_id)]
        
        for sensor in sensors:
        
            if not self.session_active:
                self.start_session()
                
            sensor.setup()

    def handle_new_sensor_data(self, sensor, data):
        
        # TODO send to all managers at some rate
        # Also check for GPS or State flags
        self._send_manager_message('all', 'new_sensor_data', (sensor.sensor_id, data))

    def handle_new_sensor_text(self, sensor, text):
        
        self._send_manager_message('all', 'new_sensor_text', (sensor.sensor_id, text))
        sensor.text_messages.append(text)
    
    def handle_new_sensor_status(self, sensor, state, health):

        sensor.update_sensor_state(state)
        sensor.update_sensor_health(health)
        
    def handle_new_sensor_heartbeat(self, sensor, unused):
        # Don't need to do anything since all sensor messages are treated as heartbeats.
        pass
        
    def handle_sensor_closed(self, sensor_id):
        
        sensor = self.find_sensor(sensor_id)
            
        sensor.update_connection_state('closed')
        
    def notify_sensor_changed(self, sensor_id, info_name, value):
        self._send_manager_message('all', 'sensor_changed', (sensor_id, info_name, value))
        
    def start_session(self):
        
        self.session_name = time.strftime("%Y-%m-%d_%H-%M-%S")
        
        self.session_active = True

    def find_sensor(self, sensor_id):
        
        for sensor in self.sensors:
            if sensor.sensor_id == sensor_id:
                return sensor
            
        raise ValueError
    
    def _send_manager_message(self, manager_id, message_type, message_body):
        
        message = {'id': self.controller_id, 'type': message_type, 'body': message_body}
        
        if manager_id == 'all': # send to all managers
            for router_id in self.managers.keys():
                self.manager_socket.send_multipart([router_id, json.dumps(message)])
        else: # just send to a single manager
            router_id = manager_id
            self.manager_socket.send_multipart([router_id, json.dumps(message)])

    def _send_sensor_message(self, sensor_id, message_type, message_body):
        
        message = {'type': message_type, 'body': message_body}

        if int(sensor_id) == 0: # send to all sensors
            for router_id in self.sensor_router_ids.values():
                self.sensor_socket.send_multipart([router_id, json.dumps(message)])
        else: # just send to single sensor
            try:
                router_id = self.sensor_router_ids[sensor_id]
                self.sensor_socket.send_multipart([router_id, json.dumps(message)])
            except KeyError:
                pass # haven't received message from sensor yet so don't know how to address it.

    def _make_sensor_name_unique(self, sensor_name):
        
        existing_sensor_names = [s.name for s in self.sensors]
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
    