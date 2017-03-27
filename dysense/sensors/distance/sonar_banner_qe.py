#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
Sensor Name:    SonarBannerQE
Manufacturer:   Banner Engineering
Sensor Type:    Distance
Other notes:    Added MCU with ADC to get data over serial port.
"""

import serial
import struct

from dysense.core.utility import find_last_index, make_unicode
from dysense.sensor_base.sensor_base import SensorBase

class SonarBannerQE(SensorBase):
    '''Receive data over serial port from microcontroller hooked up to sensor.'''

    def __init__(self, sensor_id, instrument_id, settings, context, connect_endpoint):
        '''
        Constructor. Save properties for opening serial port later.

        Args:
            sensor_id - unique ID assigned by the program.
            settings - dictionary of sensor settings. Must include:
                port - serial port name (e.g. 'COM20')
                baud - serial port rate in bits per second.
                output_period - how fast microcontroller is setup to output data (seconds)
                default_reading - distance that sensor returns when it's not getting a valid return.
                timeout_duration - how long that 'default_reading' has to be received before reporting an error.
            context - ZMQ context instance.
            connect_endpoint - endpoint on local host to receive time/commands from.

        Raises:
            ValueError - if not all settings are provided or not in correct format.
        '''
        SensorBase.__init__(self, sensor_id, instrument_id, context, connect_endpoint, throttle_sensor_read=False)

        try:
            self.port = make_unicode(settings['port'])
            self.baud = int(settings['baud'])
            self.output_period = float(settings['output_period'])
            self.default_reading = float(settings['default_reading'])
            self.timeout_duration =  float(settings['timeout_duration'])
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(e))

        # Set base class fields.  Set desired read period to be higher since MCU doesn't report at a constant rate.
        # This works because the throttle sensor read is disabled.
        self.desired_read_period = self.output_period + 1
        self.max_closing_time = 3 # seconds

        # Serial port connection.
        self.connection = None

        # Buffer of bytes that haven't been converted into a distance yet.
        self.byte_buffer = []

        # State of monitoring timeout based on constant data readings.
        if self.timeout_duration <= 0:
            self.monitor_state = 'disabled'
        else:
            self.monitor_state = 'ok'

        # How long that 'default_reading' has been received without getting another value.
        self.default_reading_elapsed = 0

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

        self.send_text('Monitoring {}.'.format('disabled' if self.monitor_state == 'disabled' else 'enabled'))

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
            new_distance = float(new_distance)
        except TypeError:
            self.send_text("Bad reported distance '{}'".format(new_distance))
            return 'error'

        current_state = self.update_monitoring_state(new_distance)

        data_ok = (current_state != 'bad_data_quality')

        self.handle_data(self.utc_time, self.sys_time, [new_distance], data_ok)

        return current_state

    def update_monitoring_state(self, new_distance):

        current_state = 'normal'

        if self.monitor_state != 'disabled':

            # Make sure distance reading is changing and not stuck at the default value.
            if self.monitor_state == 'ok':
                if new_distance == self.default_reading:
                    self.monitor_state = 'timing_out'
                    self.start_timing_out_time = self.sys_time

            if self.monitor_state == 'timing_out':

                if new_distance == self.default_reading:
                    # Still getting constant reading.
                    if self.sys_time > self.start_timing_out_time + self.timeout_duration:
                        self.monitor_state = 'timed_out'
                        self.send_text('Received default distance {} for {} straight seconds'.format(self.default_reading, self.timeout_duration))
                else: # got a different reading
                    self.monitor_state = 'ok'

            if self.monitor_state == 'timed_out':

                if new_distance == self.default_reading:
                    current_state = 'bad_data_quality'
                else: # started getting new readings again
                    self.monitor_state = 'ok'
                    self.send_text('Received non-default distance {}.'.format(new_distance))

        return current_state

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


