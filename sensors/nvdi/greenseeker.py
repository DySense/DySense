#!/usr/bin/env python

"""
Sensor Name:    GreenSeeker
Manufacturer:   Trimble
Sensor Type:    NVDI
"""

import serial

from sensor_base.sensor_base import SensorBase

class GreenSeeker(SensorBase):
    '''Receive data from GreenSeeker sensor.'''
    
    def __init__(self, sensor_id, settings, context, connect_endpoint):
        '''
        Constructor. Save properties for opening serial port later.
        
        Args:
            sensor_id - unique ID assigned by the program.
            settings - dictionary of sensor settings. Must include:
                port - serial port name (e.g. 'COM20')
                baud - serial port rate in bits per second.
                output_period - how fast greenseeker is setup to output data (seconds)
            context - ZMQ context instance.
            connect_endpoint - endpoint on local host to receive time/commands from.
            
        Raises:
            ValueError - if not all settings are provided or not in correct format.
        '''
        SensorBase.__init__(self, sensor_id, context, connect_endpoint)

        try:
            self.port = str(settings['port'])
            self.baud = int(settings['baud'])
            self.output_period = float(settings['output_period'])
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(e))
        
        # Set base class fields.
        self.desired_read_period = self.output_period
        self.max_closing_time = 3 # seconds
        
        # Serial port connection.
        self.connection = None
        
    def is_closed(self):
        '''Return true if serial port is closed.'''
        return (self.connection is None) or (not self.connection.isOpen())
    
    def close(self):
        '''Close serial port if it was open.'''
        try:
            self.connection.close()
        except (AttributeError, serial.SerialException):
            pass
        finally:
            self.connection = None
        
    def setup(self):
        '''Setup serial port.'''
        read_timeout = min(self.output_period, self.max_read_new_data_period)
        self.connection = serial.Serial(port=self.port,
                                        baudrate=self.baud,
                                        timeout=read_timeout,
                                        writeTimeout=2)
        
    def read_new_data(self):
        '''Read in new data from sensor.'''
        
        # Block until we get data or the timeout occurs.
        new_message = self.connection.readline()            
        
        if len(new_message) == 0: 
            return 'timed_out'
                
        # Split the message into the individual fields to make sure they're all there.                 
        parsed_data = [x.strip() for x in new_message.split(',')]
        
        if len(parsed_data) != 5:
            if self.last_received_data_time == 0:
                return 'normal' # ignore very first message if it is incomplete
            else:
                return 'error' # otherwise it's an issue

        try:
            internal_timestamp = int(parsed_data[0])
            nvdi = float(parsed_data[3])
            extra_vi = float(parsed_data[4])
        except ValueError:
            return 'normal' # sometimes greenseeker sends data labels as text. Don't want to do anything with those.

        self.handle_data((self.utc_time, internal_timestamp, nvdi, extra_vi))

        return 'normal'
        