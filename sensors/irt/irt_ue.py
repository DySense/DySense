#!/usr/bin/env python

"""
Sensor Name:    ThermoMETER CT-SF02-C1 
Manufacturer:   Micro Epsilon (UE)
Sensor Type:    Infrared Temperature
Modifications:  Serial -> USB FTDI 3.3V DEV-09873
"""

import serial
import struct

from sensor_base.sensor_base import SensorBase

class IRT_UE(SensorBase):
    '''Request and convert data from ThermoMETER-CT IRT sensor.'''
    
    def __init__(self, sensor_id, settings, context, connect_endpoint):
        '''
        Constructor. Save properties for opening serial port later.
        
        Args:
            sensor_id - unique ID assigned by the program.
            settings - dictionary of sensor settings. Must include:
                port - serial port name (e.g. 'COM20')
                baud - serial port rate in bits per second.
                sample_rate - how quickly to read data in Hz
            context - ZMQ context instance.
            connect_endpoint - endpoint on local host to receive time/commands from.
            
        Raises:
            ValueError - if not all settings are provided or not in correct format.
        '''
        SensorBase.__init__(self, sensor_id, context, connect_endpoint)

        try:
            self.port = str(settings['port'])
            self.baud = int(settings['baud'])
            self.sample_period = 1.0 / float(settings['sample_rate'])
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(e))
        
        # Set base class fields.
        self.desired_read_period = self.sample_period
        self.max_closing_time = 3 # seconds
        
        # Serial port connection.
        self.connection = None
        
        # How many bytes to read each time sensor sends data.
        self.bytes_to_read = 2
        
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
        read_timeout = min(self.sample_period, self.max_read_new_data_period)
        self.connection = serial.Serial(port=self.port,
                                        baudrate=self.baud,
                                        timeout=read_timeout)
        
    def request_new_data(self):
        
        # Make sure nothing extra is sitting in buffer so that next two bytes we read in should be from new request. 
        self.connection.flushInput()
        
        # Grab time here since it should, on average, represent the actual sensor measurement time.
        # If we grab it after the read/write we could have a context switch from I/O interactions.
        self.time_of_request = self.utc_time
        
        # Request a new reading from the sensor.
        self.connection.write("\x01")
        
    def read_new_data(self):
        '''Read in new data from sensor.'''
        
        # Block until we get data or the timeout occurs.
        raw_data = self.connection.read(self.bytes_to_read)
        
        if len(raw_data) < self.bytes_to_read:
            return 'timed_out'
    
        # Convert data into a temperature value.
        b1 = struct.unpack("B", raw_data[0])[0]
        b2 = struct.unpack("B", raw_data[1])[0]
        temperature = (b1 * 256.0 + b2 - 1000.0) / 10.0
        
        self.handle_data((self.time_of_request, temperature))
        
        return 'normal'
        