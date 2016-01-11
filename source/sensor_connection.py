#!/usr/bin/env python

from sensor_creation import create_sensor

class SensorConnection(object):
    
    def __init__(self, version, sensor_id, sensor_type, sensor_name, settings, metadata, observer):
        '''Constructor'''
        
        self.version = version
        self.sensor_id = sensor_id
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
        
        return self.sensor is not None
    
    def stopped_responding(self):
        return False # TODO
    
    def close(self):
        
        if self.sensor:
            # TODO send close command and wait for processes to close
            self.sensor = None
            
        self.update_connection_state('closed')
