#!/usr/bin/env python

import os
import sys
from datetime import datetime
import calendar as cal

from gps_nmea import GpsNmea

class GpsNmeaTest(GpsNmea):

    def __init__(self, sensor_id, instrument_id, settings, context, connect_endpoint):
        
        try:
            self.test_file_path = str(settings['test_file_path'])
            self.output_rate = str(settings['output_rate'])
            self.required_fix = str(settings['required_fix'])
            self.required_latlon_error = float(settings['required_error'])
            self.output_rate = float(settings['output_rate'])
            self.output_period = 1.0 / self.output_rate
        except (KeyError, ValueError, ZeroDivisionError) as e:
            raise ValueError("Bad sensor setting.  Exception {}".format(repr(e)))
        
        GpsNmea.__init__(self, self.required_fix, self.required_latlon_error, 
                         sensor_id=sensor_id, instrument_id=instrument_id,
                         context=context, connect_endpoint=connect_endpoint)
        
        self.desired_read_period = self.output_period
        
        self.test_file = None
        
    def is_closed(self):
        '''Return true if test file is closed.'''
        return self.closed
    
    def close(self):
        '''Set flag to signify that sensor is closed.'''
        self.closed = True
        
    def setup(self):
        
        if not os.path.isfile(self.test_file_path):
            raise Exception('The test file could not be found:\n\'{}\'\n'.format(self.test_file_path))
        else:
            self.test_file = open(self.test_file_path, 'r')
        
    def read_new_data(self):
        '''Read in new message from test file. Only called when not paused.'''
        
        nmea_string = self.test_file.readline().strip()
        
        # For the very first message use the current system time for UTC time instead of what's
        # in the file because if the same test file is repeatedly used then directories that use
        # the starting UTC time will all be the same.
        if self.num_data_messages_sent == 0:
            utc_override = cal.timegm(datetime.timetuple(datetime.utcnow()))
        else:
            utc_override = None
        
        success = self.process_nmea_message(nmea_string, self.sys_time, utc_override)
        
        return 'normal' if success else 'error'
