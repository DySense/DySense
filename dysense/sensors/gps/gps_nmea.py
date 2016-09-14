# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import math
import csv

from dysense.sensors.gps.nmea_parser import parse_nmea_sentence
from dysense.sensors.gps.checksum_utils import check_nmea_checksum
from dysense.sensor_base.sensor_base import SensorBase
from dysense.core.utility import utf_8_encoder

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
        self.last_gga_handle_result = 'normal'
        
        # List of message types that have been received, but not processed.
        self.unhandled_message_types = []
        
        # If set to true then will log the next position.
        self.log_next_position = False
        
        # Notes to be saved with next 'logged position'. Reset to None after every log entry.
        self.next_log_notes = None
        
        # File that's kept open to write NMEA strings to.
        self.raw_nmea_out_file = None
        
        # Keep track if data file directory changes (for example when session starts) so we can create it if we need to write files to it.
        self.last_data_file_directory = None
              
    def process_nmea_message(self, nmea_string, message_read_sys_time):
        
        self.num_messages_processed += 1

        if not check_nmea_checksum(nmea_string):
            if self.num_messages_processed == 1:
                return 'normal' # first message is likely a fragment so don't treat it as an error
            else:
                self.send_text("Invalid checksum.")
                self._write_raw_string_to_file(nmea_string)
                return 'error'
        
        try:
            sentence_type, parsed_sentence = parse_nmea_sentence(nmea_string)
        except ValueError:
            self.send_text("Failed to parse NMEA sentence. Sentence was: {}".format(nmea_string))
            self._write_raw_string_to_file(nmea_string)
            return 'error'

        # Set below based on which message is processed.  Default to last GGA result since that's really the
        # message we care about.      
        current_state = self.last_gga_handle_result
        
        if 'GGA' == sentence_type:
            current_state = self.handle_gga_message(parsed_sentence, message_read_sys_time)
            self.last_gga_handle_result = current_state

        elif 'GST' == sentence_type:
            processed_successfully = self.handle_gst_message(parsed_sentence)
            if not processed_successfully:
                current_state = 'error'
                
        else: # not processing this message type so treat it as if we never got any data.
            
            if sentence_type not in self.unhandled_message_types:
                self.unhandled_message_types.append(sentence_type)
                self.send_text('Parsed {} message which isnt being handled.'.format(sentence_type))
            
        if self.gga_count == 0 and self.num_messages_processed > 10:
            #  Should be receiving GGA messages by now..
            current_state = 'timed_out'
                                      
        # Make sure GST messages are being received if the user's trying to monitor fix accuracy.    
        if self.monitor_latlon_error and (self.gga_count > 0) and (self.gga_count % 100 == 0) and self.gst_count == 0:
            self.send_text('Received {} GGA messages without receiving a GST message'.format(self.gga_count))

        self._write_raw_string_to_file(nmea_string)

        return current_state
                                                        
    def handle_gga_message(self, data, message_read_sys_time):
        
        # Set to false below if one of the data monitoring checks fails.
        data_quality_ok = True
        
        self.gga_count += 1
                                  
        latitude = data['latitude']
        if data['latitude_direction'] == 'S':
            latitude = -latitude
 
        longitude = data['longitude']
        if data['longitude_direction'] == 'W':
            longitude = -longitude
             
        # Altitude is above ellipsoid. Don't adjust for mean-sea-level
        # since we want altitutde to be referenced from ellipsoid.
        altitude = data['altitude'] # + data['mean_sea_level']
         
        utc_time = data['utc_time']
        if math.isnan(utc_time):
            self.send_text('Invalid UTC time: {}'.format(utc_time))
            return 'error'      
        
        num_sats = data['num_satellites']
        hdop = data["hdop"]

        fix = str(data['fix_type'])
        
        if self.required_fix != 'none' and fix != self.required_fix:
            if fix != self.last_fix:
                self.send_text('Insufficient fix: {} ({})'.format(self.fix_types[fix], fix))
            self.last_fix = fix
            data_quality_ok = False
            
        elif fix != self.last_fix:  # fix is ok so just so user once 
            self.send_text('Current fix: {} ({})'.format(self.fix_types[fix], fix))
             
        self.last_fix = fix
                
        if not self.latlon_error_ok:
            # Error too high so can't handle message.
            # Don't send any text to user because that's handled in GST message.
            data_quality_ok = False
        
        enough_satellites = num_sats >= self.min_sats
        
        if not enough_satellites:
            if self.enough_satellites_last_message:
                self.send_text('Not enough satellites.')
            self.enough_satellites_last_message = enough_satellites
            data_quality_ok = False
        
        if self.min_sats > 0 and enough_satellites and not self.enough_satellites_last_message:
            self.send_text('Tracking enough satellites.')
            
        self.enough_satellites_last_message = enough_satellites
        
        self.handle_data(utc_time, message_read_sys_time, [latitude, longitude, altitude, num_sats, hdop], data_quality_ok)
        
        if self.log_next_position:
            # Log primary antenna (lat/long) reported by message to file.
            if not self.current_data_file_directory:
                self.send_text("Cannot log position because there's no valid output directory. Start a session first.")
            else:
                if not os.path.exists(self.current_data_file_directory):
                    os.makedirs(self.current_data_file_directory)
                
                log_file_path = os.path.join(self.current_data_file_directory, 'saved_positions.csv')
                
                with open(log_file_path, 'ab') as outfile:
                    writer = csv.writer(outfile)
                    writer.writerow(utf_8_encoder([utc_time, latitude, longitude, altitude, self.next_log_notes]))

                self.send_text("Saved new position with notes {}".format(self.next_log_notes))
            
            # Reset fields
            self.log_next_position = False
            self.next_log_notes = None
        
        return 'normal' if data_quality_ok else 'bad_data_quality'
        
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
    
    def log_next_position_with_notes(self, notes):
        
        self.log_next_position = True
        self.next_log_notes = notes
        
    def _write_raw_string_to_file(self, nmea_string):

        if not self.current_data_file_directory:
            return # only log data when session is valid

        if self.last_data_file_directory != self.current_data_file_directory:
            # Output directory changed so make sure it exists.
            if not os.path.exists(self.current_data_file_directory):
                os.makedirs(self.current_data_file_directory)

            self.last_data_file_directory = self.current_data_file_directory
        
            if self.raw_nmea_out_file is not None:
                # Close old file so we can open a new one at the new path.
                self.raw_nmea_out_file.close()

        if self.raw_nmea_out_file is None:
            raw_nmea_out_file_path = os.path.join(self.current_data_file_directory, 'raw_nmea_output.txt')
            self.raw_nmea_out_file = open(raw_nmea_out_file_path, 'w')

        self.raw_nmea_out_file.write(nmea_string + b'\n')
