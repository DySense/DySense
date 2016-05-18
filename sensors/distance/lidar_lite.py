#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
Sensor Name:    LidarLite
Manufacturer:   PulsedLight3d
Sensor Type:    Distance
Other notes:    Added MCU with i2c to get data over serial port.
"""

import serial
import struct
from source.utility import find_last_index, make_unicode

from sensor_base.sensor_base import SensorBase

class LidarLite(SensorBase):
    '''Receive data over serial port from microcontroller hooked up to sensor.'''
    
    def __init__(self, sensor_id, instrument_id, settings, context, connect_endpoint):
        '''
        Constructor. Save properties for opening serial port later.
        
        Args:
            sensor_id - unique ID assigned by the program.
            settings - dictionary of sensor settings. Must include:
                port - serial port name (e.g. 'COM20')
                baud - serial port rate in bits per second.
            context - ZMQ context instance.
            connect_endpoint - endpoint on local host to receive time/commands from.
            
        Raises:
            ValueError - if not all settings are provided or not in correct format.
        '''
        SensorBase.__init__(self, sensor_id, instrument_id, context, connect_endpoint, throttle_sensor_read=False)

        try:
            self.port = make_unicode(settings['port'])
            self.baud = int(settings['baud'])
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(e))
        
        # Set base class fields. Set read period to how long we want the sensor to complain after not receiving data.
        self.desired_read_period = 2
        self.max_closing_time = 3 # seconds
        
        # Serial port connection.
        self.connection = None
        
        # Buffer of bytes that haven't been converted into a distance yet.
        self.byte_buffer = []
        
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
        read_timeout = self.max_read_new_data_period
        self.connection = serial.Serial(port=self.port,
                                        baudrate=self.baud,
                                        timeout=read_timeout,
                                        writeTimeout=2)
        
    def read_new_data(self):
        '''Read in new data from sensor.'''
        
        # Block until we get data or the timeout occurs.
        new_bytes = self.connection.read()            
        
        new_distance = self.parse_distance(new_bytes)
                
        if new_distance is None:
            if self.seconds_since_sensor_setup < 1.5:
                return 'normal' # give sensor time to start up
            return 'timed_out'
        
        try:
            new_distance = int(new_distance)
        except TypeError:
            self.send_text("Bad reported distance '{}'".format(new_distance))
            return 'error'
        
        self.handle_data(self.utc_time, self.sys_time, [new_distance])

        return 'normal'
    
    def parse_distance(self, new_bytes):
        '''
        Add new bytes to the running buffer and look for a complete distance message. 
        if multiple distance messages then will only return the newest one. 
        Return None if no new message otherwise distance will be returned as a string or byte array.
        '''
        self.byte_buffer += new_bytes
        
        start_index = find_last_index(self.byte_buffer, b'$')
        if start_index < 0:
            return None
        elif start_index > 0:
            # Throw away any old data before start character.
            self.byte_buffer = self.byte_buffer[start_index:]
        
        end_index = find_last_index(self.byte_buffer, b'#')
        if end_index < 0:
            return None 
            
        distance = b''.join(self.byte_buffer[start_index+1 : end_index])

        # Throw away the distance we just read in.
        self.byte_buffer = self.byte_buffer[end_index+1:]

        return distance
