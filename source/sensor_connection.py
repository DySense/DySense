#!/usr/bin/env python

import time
from source.utility import validate_setting, validate_type, pretty
from sensor_creation import SensorCloseTimeout

class SensorConnection(object):
    
    # The keys are the possible states the connection can be in.
    # The values are the 'health' associated with each state.
    possible_states = {'closed': 'neutral',
                       'setup': 'neutral',
                       'opened': 'good',
                       'timed_out': 'bad',
                       'error': 'bad',
                       }
    
    def __init__(self, version, sensor_id, controller_id, sensor_type, heartbeat_period, settings,
                 position_offsets, orientation_offsets, instrument_id, metadata, observer, driver_factory):
        '''Constructor'''
        
        self.version = version
        self.sensor_id = str(sensor_id) # same as sensor name
        self.controller_id = str(controller_id)
        self.sensor_type = sensor_type
        self.settings = settings
        self.metadata = metadata
        #self.parameters = self.load_parameters(metadata)

        self.connection_state = 'closed'
        self.connection_health = SensorConnection.possible_states[self.connection_state]
        
        self.sensor_state = 'closed'
        self.sensor_health = 'neutral'
        self.sensor_paused = True
        
        self.overall_health = 'neutral'
        
        self.text_messages = []
        
        # Sensor offsets relative to vehicle position.
        self.position_offsets = position_offsets # Forward left up - meters
        self.orientation_offsets = orientation_offsets # Roll pitch yaw - degrees
        
        # ID of the sensor itself, not the one assigned by the program.
        self.instrument_id = instrument_id
        
        # Set to true when the sensor reports that it's closing down.
        self.closing = False
        
        # Either thread or process object that sensor driver runs in.
        self.sensor_driver = None
        
        # Notified when one of the public connection fields change.
        self.observer = observer
        
        # Used to create new sensors.
        self.driver_factory = driver_factory
        
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
                'controller_id': self.controller_id,
                'sensor_type': self.sensor_type,
                'settings': self.settings,
                #'parameters': self.parameters,
                'connection_state': self.connection_state,
                'connection_health': self.connection_health,
                'sensor_state': self.sensor_state,
                'sensor_health': self.sensor_health,
                'sensor_paused': self.sensor_paused,
                'overall_health': self.overall_health,
                'text_messages': self.text_messages,
                'position_offsets': self.position_offsets,
                'orientation_offsets': self.orientation_offsets,
                'instrument_id': self.instrument_id,
                'metadata': self.metadata}
        
    def update_sensor_type(self, new_value):
        self.sensor_type = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'sensor_type', self.sensor_type)
        
    def update_setting(self, setting_name, new_value):

        setting_metadata = [s for s in self.metadata['settings'] if s['name'] == setting_name][0]
        
        new_value = validate_setting(new_value, setting_metadata)
        
        self.settings[setting_name] = new_value
        
        self.observer.notify_sensor_changed(self.sensor_id, 'settings', self.settings)
        
    def update_connection_state(self, new_value):
        
        # Auto close if connection state closes or goes bad.
        if new_value in ['closed', 'error', 'timed_out'] and not self.is_closed():
            self.close()
        
        if self.connection_state == new_value:
            return 
        
        self.connection_state = new_value
        self.connection_health = SensorConnection.possible_states[new_value]
        self.observer.notify_sensor_changed(self.sensor_id, 'connection_state', self.connection_state)
        self.observer.notify_sensor_changed(self.sensor_id, 'connection_health', self.connection_health)
        self.update_overall_health()
        
        # Show user (and log) changes in connection state.  Don't show opened since printing two
        # messages is obnoxious.  If it's not opened then it will throw an error or timeout.
        if new_value != 'opened':
            self.observer.handle_new_sensor_text(self, 'Driver {}'.format(pretty(new_value)))
        
    def update_sensor_state(self, new_value):
        self.sensor_state = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'sensor_state', self.sensor_state)
        
    def update_sensor_health(self, new_value):
        self.sensor_health = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'sensor_health', self.sensor_health)
        self.update_overall_health()
        
    def update_sensor_paused(self, new_value):
        self.sensor_paused = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'sensor_paused', self.sensor_paused)
        
    def update_overall_health(self):
        
        if self.connection_health == 'bad' or self.sensor_health == 'bad':
            self.overall_health = 'bad'
        elif self.connection_health == 'good' and self.sensor_health == 'good':
            self.overall_health = 'good'
        else:
            self.overall_health = 'neutral'
        self.observer.notify_sensor_changed(self.sensor_id, 'overall_health', self.overall_health)
        
        # Make sure an issue is active if the health is bad.
        if self.overall_health == 'bad':
            if self.connection_health == 'bad' and self.sensor_health == 'bad':
                issue_reason = "Bad driver state '{}' and bad sensor state '{}'".format(self.connection_state, self.sensor_state)
            elif self.connection_health == 'bad':
                issue_reason = "Bad driver state '{}'".format(self.connection_state)
            else: # just sensor health is bad
                issue_reason = "Bad sensor state '{}'".format(self.sensor_state)
        
            self.observer.try_create_issue(self.observer.controller_id, self.sensor_id, 'unhealthy_sensor', issue_reason, 'error')
        else:
            # Resolve any possible old issues dealing with sensor health.
            self.observer.try_resolve_issue(self.sensor_id, 'unhealthy_sensor')
        
    def update_position_offsets(self, new_value):
        
        validated_offsets = []
        for offset in new_value:
            validated_offsets.append(validate_type(offset, 'float'))
        
        self.position_offsets = validated_offsets
        self.observer.notify_sensor_changed(self.sensor_id, 'position_offsets', self.position_offsets)
        
    def update_orientation_offsets(self, new_value):
        
        validated_offsets = []
        for offset in new_value:
            validated_offsets.append(validate_type(offset, 'float'))
        
        self.orientation_offsets = validated_offsets
        self.observer.notify_sensor_changed(self.sensor_id, 'orientation_offsets', self.orientation_offsets)
        
    def update_instrument_id(self, new_value):
        self.instrument_id = new_value
        self.observer.notify_sensor_changed(self.sensor_id, 'instrument_id', self.instrument_id)
        
    def reset(self):
        '''Reset all fields that may have changed last time sensor was setup/running.'''
        
        self.update_connection_state('closed')
        self.update_sensor_state('closed')
        self.update_sensor_health('neutral')
        self.update_sensor_paused(True)
        self.text_messages = []
        self.closing = False
        self.last_message_processing_time = 0
        self.last_received_message_time = 0
        self.last_sent_heartbeat_time = 0
        self.interface_connection_time = 0
        self.num_messages_received = 0
        
    def setup(self):
        
        if self.sensor_driver:
            return # Need to call close() first before making a new sensor driver instance
        
        self.reset();
        
        try:
            self.sensor_driver = self.driver_factory.create_sensor(self.sensor_type, self.sensor_id, self.instrument_id, self.settings)
        except Exception as e:
            self.observer.handle_new_sensor_text(self, "{}".format(repr(e)))
        
        if self.sensor_driver:
            self.update_connection_state('setup')
            # Save when we setup sensor to help for detecting timeout if sensor never responds at all.
            self.interface_connection_time = time.time()
        else:
            self.update_connection_state('error')

    def close(self):
        '''Close down process or thread associated with connection.  Need to send close message before calling this.'''
        
        # Mark that sensor is closing so it doesn't try to re-open when new messages arrive.
        self.closing = True
        
        try:
            if self.sensor_driver:
                self.sensor_driver.close(timeout=3) # TODO allow sensor driver to specify timeout
                self.sensor_driver = None
            else:
                # There's no driver to close down.  Most likely this is the user hitting close after there's been an error
                # so just reset the driver state since the user is essentially 'acknowledging' they say what was wrong.
                self.update_sensor_state('closed')
                self.update_sensor_health('neutral')
                self.update_sensor_paused(True)
        except SensorCloseTimeout:
            pass # TODO notify that sensor didn't close down in required time
            
        self.update_connection_state('closed')
        
    def is_closed(self):
        '''Return true if sensor driver isn't closed.'''
        return self.sensor_driver is None

    def stopped_responding(self):
        '''Return true if it's been too long since we've received a new message from sensor.'''
        
        if self.connection_state in ['closed']:
            return False # Shouldn't be receiving messages.
        
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
