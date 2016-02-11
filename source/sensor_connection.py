#!/usr/bin/env python

import time
from sensor_creation import create_sensor

class SensorConnection(object):
    
    def __init__(self, version, sensor_id, sensor_type, sensor_name, heartbeat_period, settings, metadata, observer):
        '''Constructor'''
        
        self.version = version
        self.sensor_id = str(sensor_id)
        self.sensor_type = sensor_type
        self.sensor_name = sensor_name
        self.settings = settings
        self.metadata = metadata
        #self.parameters = self.load_parameters(metadata)

        self.connection_state = 'closed'
        self.sensor_state = 'unknown'
        self.sensor_health = 'N/A'
        
        self.text_messages = []
        
        self.sensor = None
        
        self.observer = observer
        
        # How often (in seconds) we should receive a new message from sensor and how often we should send one back.
        self.heartbeat_period = heartbeat_period
        
        # If we don't receive a new message in this time then consider sensor dead. (in seconds) 
        self.sensor_timeout_thresh = self.heartbeat_period * 10
        
        # How long to wait for sensor to send first message before timing out. (in seconds)
        self.max_time_to_receive_message = self.sensor_timeout_thresh * 1.5
        
        # Last system time that we tried to process new messages from sensor.
        self.last_message_processing_time = 0
        
        # Last system time that we received a new message from sensor.
        self.last_received_message_time = 0
        
        # Last time we sent out a heartbeat message.
        self.last_sent_heartbeat_time = 0
        
        # Time that interface was connected to sensor.
        self.interface_connection_time = 0
    
        # How many message have been received from sensor.
        self.num_messages_received = 0
        
    @property
    def public_info(self):
        
        return {'sensor_id': self.sensor_id,
                'sensor_type': self.sensor_type,
                'sensor_name': self.sensor_name,
                'settings': self.settings,
                #'parameters': self.parameters,
                'connection_state': self.connection_state,
                'sensor_state': self.sensor_state,
                'sensor_health': self.sensor_health,
                'text_messages': self.text_messages,
                'metadata': self.metadata}
        
    def reset(self):
        
        self.update_connection_state('closed')
        self.update_sensor_state('unknown')
        self.update_sensor_health('N/A')
        
        self.text_messages = []
        
    def update_sensor_type(self, new_value):
        self.sensor_type = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'sensor_type', self.sensor_type)
        
    def update_sensor_name(self, new_value):
        self.sensor_name = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'sensor_name', self.sensor_name)
        
    def update_setting(self, setting_name, new_value):
        raise NotImplementedError
        # TODO also handle is_main*
        self.observer.notify_sensor_changed(self.sensor_id, 'sensor_type', self.sensor_type)
        
    def update_connection_state(self, new_value):
        self.connection_state = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'connection_state', self.connection_state)
        
    def update_sensor_state(self, new_value):
        self.sensor_state = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'sensor_state', self.sensor_state)
        
    def update_sensor_health(self, new_value):
        self.sensor_health = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'sensor_health', self.sensor_health)
        
    def setup(self, context, local_endpoint, remote_endpoint):
        
        self.sensor = create_sensor(self.sensor_type, self.sensor_id, self.settings, context, local_endpoint, remote_endpoint)
        
        if self.sensor:
            self.update_connection_state('setup')
        
        # Save when we setup sensor to help for detecting timeout if sensor never responds at all.
        self.interface_connection_time = time.time()
        
        return self.sensor is not None
    
    def close(self):
        
        if self.sensor:
            # TODO send close command and wait for processes to close
            self.sensor = None
            
        self.update_connection_state('closed')

    def stopped_responding(self):
        '''Return true if it's been too long since we've received a new message from sensor.'''
        if self.interface_connection_time == 0 or self.last_message_processing_time == 0:
            # Haven't tried to receive any messages yet so can't know if we're timed out.
            return False 
        
        if self.num_messages_received == 0:
            # Give sensor more time to send first message.
            time_since_connecting = self.last_message_processing_time - self.interface_connection_time
            return time_since_connecting > self.max_time_to_receive_message
            
        # We're getting messages so use normal timeout.
        time_since_last_message = self.last_message_processing_time - self.last_received_message_time
        return time_since_last_message > self.sensor_timeout_thresh
            
    def need_to_send_heartbeat(self):
        '''Return true if it's time to send a heartbeat message to sensor.'''
        time_since_last_heartbeat = time.time() - self.last_sent_heartbeat_time 
        return time_since_last_heartbeat > self.heartbeat_period
