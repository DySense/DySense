#!/usr/bin/env python

import serial

from gps_nmea import GpsNmea

class GpsNmeaSerial(GpsNmea):
    '''Receive and process data from GPS using NMEA format.'''
    
    def __init__(self, sensor_id, settings, context, connect_endpoint):
        '''
        Constructor. Save properties for opening serial port later.
        
        Args:
            sensor_id - unique ID assigned by the program.
            settings - dictionary of sensor settings. Must include:
                port - serial port name (e.g. 'COM20')
                baud - serial port rate in bits per second.
                message_rate - how fast GPS is setup to output messages (Hz)
            context - ZMQ context instance.
            connect_endpoint - endpoint on local host to receive time/commands from.
            
        Raises:
            ValueError - if not all settings are provided or not in correct format.
        '''
        try:
            self.port = str(settings['port'])
            self.baud = int(settings['baud'])
            self.message_period = 1.0 / float(settings['message_rate'])
            self.required_fix = str(settings['required_fix'])
            self.required_latlon_error = float(settings['required_error'])
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(e))
        
        GpsNmea.__init__(self, self.required_fix, self.required_latlon_error, 
                         sensor_id=sensor_id, context=context, connect_endpoint=connect_endpoint)
        
        # Set base class fields.
        self.desired_read_period = self.message_period
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
        read_timeout = min(self.message_period, self.max_read_new_data_period)
        self.connection = serial.Serial(port=self.port,
                                        baudrate=self.baud,
                                        timeout=read_timeout,
                                        writeTimeout=2)
        
    def read_new_data(self):
        '''Read in new data from sensor.'''
        
        # Block until we get data or the timeout occurs.
        nmea_string = self.connection.readline().strip()
        
        if len(nmea_string) == 0:
            return 'timed_out'
    
        success = self.process_nmea_message(nmea_string, self.sys_time)
        
        return 'normal' if success else 'error'
        
