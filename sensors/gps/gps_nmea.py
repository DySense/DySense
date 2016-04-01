import os
import math

from nmea_parser import parse_nmea_sentence
from checksum_utils import check_nmea_checksum
from sensor_base.sensor_base import SensorBase

class GpsNmea(SensorBase):
    
    def __init__(self, required_fix, max_allowed_latlon_error, min_sats, **kargs):
        SensorBase.__init__(self, wait_for_valid_time=False, **kargs)
    
        # Fix types reported by GGA message.
        self.fix_types = {'0': 'None',
                          '1': 'GPS',
                          '2': 'DGPS',
                          '3': 'PPS',
                          '4': 'Fixed RTK',
                          '5': 'Float/Location RTK or OmniStar',
                          '6': 'Dead Reckoning',
                          '7': 'Manual',
                          '8': 'Simulation'}
    
        # GPS fix type that's required for class to report data.
        self.required_fix = required_fix.lower()
        if required_fix != 'none' and required_fix not in self.fix_types:
            raise Exception('Invalid required fix')
        
        # The maximum lat/long error that is allowed before this class stops reporting data.
        # If zero or negative then disables 
        self.max_allowed_latlon_error = float(max_allowed_latlon_error)
        
        # If the # of satellites drops below this then class stops reporting data.
        self.min_sats = min_sats
        
        # Set to true if user specified a valid lat/lon error to monitor.
        self.monitor_latlon_error = self.max_allowed_latlon_error > 0
        
        if self.monitor_latlon_error:
            self.send_text('Maximum lat/lon error set to {}'.format(self.max_allowed_latlon_error))
        
        # Set to false if either latitude or longitude error gets too high.
        self.latlon_error_ok = True if not self.monitor_latlon_error else False
        
        # Last max lat/lon error received from GST message.
        self.last_latlon_error = -1.0
        
        # Set to true if there was enough satellites last time GGA message was received.
        self.enough_satellites_last_message = True
        
        # Initialize last fix to something that won't occur so user will get notified of initial fix.
        self.last_fix = '-1'
        
        # How many times specific messages have been received.
        self.gga_count = 0
        self.gst_count = 0
        
        # How many messages have attempted to be processed.
        self.num_messages_processed = 0
        
        # Last result returned from handle_gga_message() 
        self.last_gga_handle_result = False
              
    def process_nmea_message(self, nmea_string, message_read_time, utc_override=None):
        
        self.num_messages_processed += 1

        if not check_nmea_checksum(nmea_string):
            if self.num_messages_processed > 1:
                # Only send message if wasn't first message because sometimes first message isn't complete.
                self.send_text("Invalid checksum. Sentence was: {}".format(nmea_string))
            return False
        
        try:
            sentence_type, parsed_sentence = parse_nmea_sentence(nmea_string)
        except ValueError:
            self.send_text("Failed to parse NMEA sentence. Sentence was: {}".format(nmea_string))
            return False

        # Set to true if message is handled successfully.        
        processed_successfully = False
        
        if 'GGA' == sentence_type:
            processed_successfully = self.handle_gga_message(parsed_sentence, message_read_time, utc_override)
            self.last_gga_handle_result = processed_successfully

        elif 'GST' == sentence_type:
            processed_successfully = self.handle_gst_message(parsed_sentence)
            if processed_successfully:
                # Override with last GGA result because we don't want the state of the driver to be 'good' or 'normal'
                # solely based on whether or not processing a GST message was successful.
                processed_successfully = self.last_gga_handle_result
                                      
        # Make sure GST messages are being received if the user's trying to monitor fix accuracy.    
        if self.monitor_latlon_error and (self.gga_count % 100 == 0) and self.gst_count == 0:
            self.send_text('Received {} GGA messages without receiving a GST message'.format(self.gga_count))
                                          
        return processed_successfully
                                                        
    def handle_gga_message(self, data, message_read_time, utc_override):
        
        self.gga_count += 1
                                  
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
        
        num_sats = data['num_satellites']
        hdop = data["hdop"]

        fix = str(data['fix_type'])
        
        if self.required_fix != 'none' and fix != self.required_fix:
            if fix != self.last_fix:
                self.send_text('Insufficient fix: {} ({})'.format(self.fix_types[fix], fix))
            self.last_fix = fix
            return False # bad fix 
            
        if fix != self.last_fix:  
            self.last_fix = fix
            self.send_text('Current fix: {}'.format(self.fix_types[fix]))
                
            if utc_override:
                utc_time = utc_override
                
        if not self.latlon_error_ok:
            # Error too high so can't handle message.
            return False
        
        enough_satellites = num_sats >= self.min_sats
        
        if not enough_satellites:
            if self.enough_satellites_last_message:
                self.send_text('Not enough satellites.')
            self.enough_satellites_last_message = enough_satellites
            return False
        
        if self.min_sats > 0 and enough_satellites and not self.enough_satellites_last_message:
            self.send_text('Tracking enough satellites.')
            
        self.enough_satellites_last_message = enough_satellites    
             
        self.handle_data((utc_time, message_read_time, latitude, longitude, altitude, num_sats, hdop))
        
        return True # successfully handled
        
    def handle_gst_message(self, data):
            
        self.gst_count += 1
            
        if not self.monitor_latlon_error:
            return True # don't want to do anything with message so consider handling it successful.
            
        # All errors in meters
        lat_error = data['latitude_error'] 
        long_error = data['longitude_error']
        
        latlon_error = max(lat_error, long_error)
        
        # remember if error was ok so we can determine below whether or not to notify user.
        self.latlon_error_was_just_ok = self.latlon_error_ok
        
        self.latlon_error_ok = latlon_error <= self.max_allowed_latlon_error
        
        # Notify user if state of the error being ok / not ok has changed.
        if self.latlon_error_ok:
            
            if not self.latlon_error_was_just_ok:
                self.send_text('Required lat/long error achieved.'.format(self.max_allowed_latlon_error))
                self.last_latlon_error = latlon_error
                
        else: # error too high.
            
            if latlon_error != self.last_latlon_error:
                self.send_text('Current lat/long error of {}m is too large.'.format(latlon_error))
                self.last_latlon_error = latlon_error                       

        return True # successfully handled
