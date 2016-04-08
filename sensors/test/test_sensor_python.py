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
    
    def __init__(self, sensor_id, instrument_id, settings, context, connect_endpoint):
        '''
        Constructor.
        
        Args:
            sensor_id - unique ID assigned by the program.
            settings - dictionary of sensor settings. Must include:
                output_rate - how fast to output data (Hz)
                test_float - any number that is a floating point number
                test_int - should be between 0 and 100. 
                test_string - any string that's not empty
                test_bool - either true / false. Just used for testing UI.
            context - ZMQ context instance.
            connect_endpoint - endpoint on local host to receive time/commands from.
            
        Raises:
            ValueError - if not all settings are provided or not in correct format.
        '''
        SensorBase.__init__(self, sensor_id, instrument_id, context, connect_endpoint)

        try:
            self.output_rate = float(settings['output_rate'])
            self.test_float = float(settings['test_float'])
            self.test_int = int(settings['test_int'])
            self.test_string = str(settings['test_string'])
            self.test_bool = bool(settings['test_bool'])
            self.output_period = 1.0 / self.output_rate
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(repr(e)))
        
        # Set base class fields.
        self.desired_read_period = self.output_period
        self.max_closing_time = 2
        
        # Counter for each time data has been generated.
        self.counter = 0
        
        # Flag that can be overridden with special command for testing.
        self.data_quality_ok = True
        
        # Flag to signify that the sensor is 'closed'
        self.closed = True

    def is_closed(self):
        '''Return true if sensor is closed.'''
        return self.closed
    
    def close(self):
        '''Set flag to signify that sensor is closed.'''
        self.closed = True
        
    def read_new_data(self):
        '''Generate new data to output and return current read state.'''
        
        new_data = [str(self.counter), random.randint(0, 100), random.random(), self.sys_time]
        
        self.handle_data(self.utc_time, self.sys_time, new_data, self.data_quality_ok)
        
        self.counter += 1
        
        return 'normal' if self.data_quality_ok else 'bad_data_quality'
        
    def handle_special_command(self, command):
        
        if command == 'crash':
            raise Exception("Intentional crash for testing.")
        
        if command == 'bad_data':
            self.data_quality_ok = False
            
        if command == 'good_data':
            self.data_quality_ok = True
        
if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser(description='''Test Sensor''')
    parser.add_argument('id' )
    parser.add_argument('settings')
    parser.add_argument('connect_endpoint')
    
    import json
    args = vars(parser.parse_args())
    sensor_id = args['id']
    settings = json.loads(args['settings'])
    connect_endpoint = args['connect_endpoint']
    
    import zmq
    context = zmq.Context()

    sensor = TestSensor(sensor_id, settings, context, connect_endpoint)
    
    print "starting test sensor!"
    sensor.run()
    print "closing test sensor!"
        