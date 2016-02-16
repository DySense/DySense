#!/usr/bin/env python

import os
import sys
import argparse
import socket
import serial
import math
import time

from gps_nmea import GpsNmea

class GpsNmeaTest(GpsNmea):

    def __init__(self, sensor_id, settings, context, connect_endpoint):
        
        try:
            self.test_file_path = str(settings['test_file_path'])
            self.output_rate = str(settings['output_rate'])
            self.required_fix = str(settings['required_fix'])
            self.required_precision = float(settings['required_precision'])
            self.output_rate = float(settings['output_rate'])
            self.output_period = 1.0 / self.output_rate
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(repr(e)))
        
        GpsNmea.__init__(self, self.required_fix, self.required_precision, 
                         sensor_id=sensor_id, context=context, connect_endpoint=connect_endpoint)
        
        self.min_loop_period = self.output_period
        
        self.test_file = None
        
    def is_closed(self):
        '''Return true if test file is closed.'''
        return self.closed
    
    def close(self):
        '''Set flag to signify that sensor is closed.'''
        self.closed = True
        
    def setup(self):
        
        if not os.path.isfile(self.test_file_path):
            self.send_text('The test file could not be found:\n\'{}\'\n'.format(self.test_file_path))
            self.health = 'bad' # TODO have a way to signify error
        else:
            self.test_file = open(self.test_file_path, 'r')
        
    def read_new_data(self):
        '''Read in new message from test file. Only called when not paused.'''
        
        if self.test_file is None:
            self.health = 'bad'
            return
        
        nmea_string = self.test_file.readline().strip()
        
        success = self.process_nmea_message(nmea_string)
        
        # TODO intelligent wait based off when next message should be read
        
        self.health = 'good' if success else 'bad'