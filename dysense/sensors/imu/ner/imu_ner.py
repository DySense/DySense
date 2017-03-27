#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
Sensor Name:    ImuNer
Manufacturer:   New Earth Robotics (NER)
Sensor Type:    Inertial Measurement Unit
"""

import serial
import struct

from dysense.sensor_base.sensor_base import SensorBase
from dysense.core.utility import make_unicode
from dysense.sensors.imu.ner.imu_glob.glob_link import GlobParser
from dysense.sensors.imu.ner.imu_glob.imu_glob import GlobID, AssertMessage, DebugMessage, UserData

class ImuNer(SensorBase):
    '''Receive orientation and battery information from IMU board.'''

    def __init__(self, sensor_id, instrument_id, settings, context, connect_endpoint):
        '''
        Constructor. Save properties for opening serial port later.
        '''
        SensorBase.__init__(self, sensor_id, instrument_id, context, connect_endpoint, throttle_sensor_read=False)

        try:
            self.port = make_unicode(settings['port'])
            self.baud = int(settings['baud'])
            self.receive_period = 1.0 / float(settings['receive_rate'])
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(e))

        # Set base class fields.  Set read period higher since sensor read throttle is disabled.
        self.desired_read_period = self.receive_period + 1
        self.max_closing_time = 3 # seconds

        # Serial port connection.
        self.connection = None

        # Used for converting raw data into glob messages.
        self.parser = GlobParser()

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
        read_timeout = min(self.receive_period, self.max_read_new_data_period)
        self.connection = serial.Serial(port=str(self.port),
                                        baudrate=self.baud,
                                        timeout=read_timeout,
                                        writeTimeout=2)

    def request_new_data(self):

        pass # data isn't requested, just sent.

    def read_new_data(self):
        '''Read in new data from sensor.'''

        # Block until we get data or the timeout occurs.
        raw_data = bytearray(self.connection.read(1))

        if len(raw_data) == 0:
            if self.seconds_since_sensor_setup < 1:
                return 'normal' # give sensor time to start up
            return 'timed_out'

        # Convert raw bytes into glob messages.
        new_messages = self.parser.parse_data(raw_data)

        for message in new_messages:
            self.handle_new_message(message['id'], message['instance'], message['body'])
            #self.send_text('{} - {}'.format(message['id'], message['packet_num']))

        return 'normal' if len(new_messages) > 0 else 'timed_out'

    def handle_new_message(self, id, instance, body):

        if id == GlobID.AssertMessage:
            msg = AssertMessage.from_bytes(body)
            if msg.valid:
                self.send_text('ASSERT:' + make_unicode(msg.message))

        elif id == GlobID.DebugMessage:
            msg = DebugMessage.from_bytes(body)
            if msg.valid:
                self.send_text('DEBUG:' + make_unicode(msg.message))

        elif id == GlobID.UserData:
            msg = UserData.from_bytes(body)

            self.handle_data(self.utc_time, self.sys_time, (msg.roll, msg.pitch, msg.yaw, msg.battery))
