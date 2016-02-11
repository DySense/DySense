#!/usr/bin/env python

"""
Sensor Name:    Test Sensor
Manufacturer:   None
Sensor Type:    Generates its own data.
"""

import time
import random

from sensor_base.sensor_base import SensorBase

class TestSensor(SensorBase):
    ''''''
    
    def __init__(self, sensor_id, settings, context, connect_endpoint):
        '''
        Constructor. Save properties for opening serial port later.
        
        Args:
            settings - dictionary of sensor settings. Must include:
                output_rate - how fast to output data (Hz)
                test_float - any number that is a floating point number
                test_int - should be between 0 and 100. 
                test_string - any string that's not empty
                test_bool - either true / false. Just used for testing UI.
            receive_port - endpoint on local host to receive time/commands from.
            
        Raises:
            ValueError - if not all settings are provided or not in correct format.
        '''
        SensorBase.__init__(self, sensor_id, context, connect_endpoint)

        try:
            self.output_rate = float(settings['output_rate'])
            self.test_float = float(settings['test_float'])
            self.test_int = int(settings['test_int'])
            self.test_string = str(settings['test_string'])
            self.test_bool = bool(settings['test_bool'])
            self.output_period = 1.0 / self.output_rate
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(e))
        
        # Set base class fields.
        self.min_loop_period = self.output_period
        self.max_closing_time = self.output_period + 1
        
        # Counter for each time data has been generated.
        self.counter = 0
        
        # Flag to signify that the sensor is 'closed'
        self.closed = True

    def is_closed(self):
        '''Return true if sensor is closed.'''
        return self.closed
    
    def close(self):
        '''Set flag to signify that sensor is closed.'''
        self.closed = True
        
    def read_new_data(self):
        '''Generate new data to output. Only called when not paused.'''
        
        new_data = (self.time, str(self.counter), random.randint(0, 100), random.random(), time.time())
        
        self.handle_data(new_data)
        
        self.health = 'good'
        
        self.counter += 1
        
    def handle_special_command(self, command):
        
        if command == 'crash':
            raise Exception("Intentional crash for testing.")
        
        