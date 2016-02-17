#!/usr/bin/env python

import os
import sys
import argparse
import socket
import serial
import math
import time

if os.name == 'nt':
    import winsound

from nmea_parser import parse_nmea_sentence
from checksum_utils import check_nmea_checksum
from sensor_base.sensor_base import SensorBase

class GpsNmea(SensorBase):
    
    def __init__(self, required_fix, required_precision, **kargs):
        SensorBase.__init__(self, wait_for_valid_time=False, **kargs)
    
        self.fix_types = {'0': 'None',
                          '1': 'GPS',
                          '2': 'DGPS',
                          '3': 'PPS',
                          '4': 'Fixed RTK',
                          '5': 'Float/Location RTK or OmniStar',
                          '6': 'Dead Reckoning',
                          '7': 'Manual',
                          '8': 'Simulation'}
    
        self.required_fix = required_fix.lower()
        self.required_precision = float(required_precision)

        if required_fix != 'none' and required_fix not in self.fix_types:
            raise Exception('Invalid required fix')
        
        # Initialize last_fix and last_error as values that will never occur
        self.last_fix = '-1'
        self.data_quality_is_good = False
        self.last_error = -1.0
        self.gga_count = 0 # how many GGA messages have been received.
        
        if self.required_precision > 0:
            self.send_text('Required precision set to {}'.format(required_precision))
            # Override to false until we know we have good precision.
            self.data_quality_is_good = False
              
        if self.required_fix != 'none':
            self.send_text('Waiting for required fix of {}'.format(self.fix_types[required_fix]))
              
    def process_nmea_message(self, nmea_string):
        
        # time (in seconds) that the most recent nmea message was read in.
        message_read_time = time.time()

        if not check_nmea_checksum(nmea_string):
            return False
        
        parsed_sentence = parse_nmea_sentence(nmea_string)
        if not parsed_sentence:
            self.send_text("Failed to parse NMEA sentence. Sentence was: {}".format(nmea_string))
            return False
                    
        if 'GGA' in parsed_sentence:
                                                        
            self.gga_count += 1
                             
            data = parsed_sentence['GGA']
                       
            latitude = data['latitude']
            if data['latitude_direction'] == 'S':
                latitude = -latitude
     
            longitude = data['longitude']
            if data['longitude_direction'] == 'W':
                longitude = -longitude
                 
            # Altitude is above ellipsoid, so adjust for mean-sea-level
            altitude = data['altitude'] + data['mean_sea_level']
             
            utc_time = data['utc_time']
            if math.isnan(utc_time):
                self.send_text('Invalid UTC time: {}'.format(utc_time))
                return False
            
            if True: # self.data_quality_is_good: # TODO 
                
                fix = str(data['fix_type'])
                
                if self.required_fix != 'none' and fix != self.required_fix:
                    
                    if fix != self.required_fix:
                        self.last_fix = fix
                        self.send_text('Insufficient fix: {}'.format(self.fix_types[fix]))
                        
                    return False # bad fix 
                    
                if fix != self.last_fix:  
                    self.last_fix = fix
                    self.send_text('Current fix: {}'.format(self.fix_types[fix]))
                    
                self.handle_data({'utc_time': utc_time,
                                  'sys_time': message_read_time,
                                  'position': (latitude, longitude, altitude)},
                                 labeled=True)
    
            return True # success
