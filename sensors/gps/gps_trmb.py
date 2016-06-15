# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import math
import utm
import csv

from nmea_parser import parse_nmea_sentence
from checksum_utils import check_nmea_checksum
from sensor_base.sensor_base import SensorBase
from source.utility import utf_8_encoder

rad2deg = 180.0 / math.pi
deg2rad = math.pi / 180.0

# TODO make this a sensor setting
yaw_offset = 90 * deg2rad

class GpsTrimble(SensorBase):
    
    def __init__(self, required_fix, min_sats, **kargs):
        SensorBase.__init__(self, wait_for_valid_time=False, **kargs)
    
        # Fix types reported by GGK message.
        self.ggk_fix_types = {'0': 'None',
                              '1': 'Autonomous GPS',
                              '2': 'RTK Float',
                              '3': 'RTK Fix',
                              '4': 'DGPS, code phase only',
                              '5': 'SBAS (WAAS/EGNOS/MSAS)',
                              '6': 'RTK float 3D Network',
                              '7': 'RTK fixed 3D Network',
                              '8': 'RTK float 2D Network',
                              '9': 'RTK fixed 2D Network',
                              '10': 'OmniSTAR HP/XP solution',
                              '11': 'OmniSTAR VBS solution',
                              '12': 'Location RTK solution',
                              '13': 'Beacon DGPS'}
        
        # Fix types reported by AVR message. (currently just using ggk to monitor fix)
        #self.avr_fix_types = {'0': 'None',
        #                      '1': 'Autonomous GPS',
        #                      '2': 'RTK Float',
        #                      '3': 'RTK Fix',
        #                      '4': 'DGPS, code phase only'}
    
        # Fix type that's required for class to report data.
        self.required_fix = required_fix.lower()
        if required_fix != 'none' and required_fix not in self.ggk_fix_types:
            raise Exception('Invalid required fix')
        
        # If the # of satellites drops below this then class stops reporting data.
        self.min_sats = min_sats
        
        # Set to true if there was enough satellites last time GGK message was received.
        self.enough_satellites_last_message = True
        
        # Initialize last fix to something that won't occur so user will get notified of initial fix.
        self.last_fix = '-1'
        
        # Last received messages.
        self.ggk = None
        self.avr = None
        
        # How many times specific messages have been received.
        self.ggk_count = 0
        self.avr_count = 0
        
        # Last result from processing a message.
        self.last_state = 'normal'
        
        # How many messages have attempted to be processed.
        self.num_messages_processed = 0
        
        # UTC times of messages that were last used to combine into a single position + yaw.
        self.last_used_ggk_time = 0
        self.last_used_avr_time = 0
        
        # List of message types that have been received, but not processed.
        self.unhandled_message_types = []
        
        # If set to true then will log the next position.
        self.log_next_position = False
        
        # Notes to be saved with next 'logged position'. Reset to None after every log entry.
        self.next_log_notes = None
              
    def process_nmea_message(self, nmea_string, message_read_sys_time, utc_override=None):
        
        self.num_messages_processed += 1

        if not check_nmea_checksum(nmea_string):
            if self.num_messages_processed > 1:
                # Only send message if wasn't first message because sometimes first message isn't complete.
                self.send_text("Invalid checksum.")
                self.send_text(nmea_string)
            return 'error'
        
        try:
            sentence_type, parsed_sentence = parse_nmea_sentence(nmea_string)
        except ValueError:
            self.send_text("Failed to parse NMEA sentence. Sentence was: {}".format(nmea_string))
            return 'error'
        
        # Set below based on which message is processed.  Default to last state in case it's not updated.
        current_state = self.last_state
                
        if 'AVR' == sentence_type:
            processed_successfully = self.handle_avr_message(parsed_sentence)
            if not processed_successfully:
                current_state = 'error'

        elif 'GGK' == sentence_type:
            processed_successfully = self.handle_ggk_message(parsed_sentence)
            if processed_successfully:
                current_state = self.combine_position_and_orientation(self.ggk['utc_time'], message_read_sys_time, utc_override)
                
                if self.log_next_position:
                    # Log primary antenna (lat/long) reported by GGK to file.
                    if not self.current_data_file_directory:
                        self.send_text("Cannot log position because there's no valid output directory. Start a session first.")
                    else:
                        if not os.path.exists(self.current_data_file_directory):
                            os.makedirs(self.current_data_file_directory)
                        
                        log_file_path = os.path.join(self.current_data_file_directory, 'saved_positions.csv')
                        
                        with open(log_file_path, 'ab') as outfile:
                            writer = csv.writer(outfile)
                            writer.writerow(utf_8_encoder([self.ggk['utc_time'], self.ggk['latitude'], self.ggk['longitude'], self.ggk['altitude'], self.next_log_notes]))
    
                        self.send_text("Saved new position with notes {}".format(self.next_log_notes))
                    
                    # Reset fields
                    self.log_next_position = False
                    self.next_log_notes = None
            
            else:
                current_state = 'error'
                
        else: # not processing this message type so treat it as if we never got any data.
            
            if sentence_type not in self.unhandled_message_types:
                self.unhandled_message_types.append(sentence_type)
                self.send_text('Parsed {} message which isnt being handled.'.format(sentence_type))
            
        if (self.ggk_count == 0 or self.avr_count == 0) and self.num_messages_processed > 10:
            current_state = 'timed_out'
                                      
        self.last_state = current_state
                                      
        return current_state
    
    def combine_position_and_orientation(self, utc_time, sys_time, utc_override=None):
        
        if self.ggk_count == 0 or self.avr_count == 0:
            return 'normal' # let driver determine if timed out or not.
        
        new_ggk_message = self.ggk['utc_time'] > self.last_used_ggk_time
        new_avr_message = self.avr['utc_time'] > self.last_used_avr_time
        
        if not new_ggk_message or not new_avr_message:
            return 'normal' # let driver determine if timed out or not.
        
        # Save this so we know for next time.
        self.last_used_ggk_time = self.ggk['utc_time']
        self.last_used_avr_time = self.avr['utc_time']
        
        # Assume data is good enough to use unless one of the checks below fails.
        data_quality_ok = True

        # Make sure that there isn't a large time difference between the messages.
        utc_difference = abs(self.ggk['utc_time'] - self.avr['utc_time'])
        if utc_difference > 1:
            self.send_text("Large utc difference between AVR and GGK: {}".format(utc_difference))
            data_quality_ok = False

        # Need to add in offset due to antenna configuration.  For example in a 'roll' mount configuration
        # the heading would read 90 degrees when facing north.
        measured_yaw = self.avr['yaw_deg'] * deg2rad
        corrected_yaw = measured_yaw - yaw_offset

        # Need to flip sign since in ENU we should increase CCW but trimble measures CW
        corrected_yaw *= -1.0

        # Also need to permanently add 90 degrees since facing 'east' is zero degrees in ENU.
        corrected_yaw += math.pi / 2
    
        # Cap corrected yaw between +/- PI
        while corrected_yaw > +math.pi: corrected_yaw -= 2 * math.pi
        while corrected_yaw < -math.pi: corrected_yaw += 2 * math.pi

        # Convert to UTM so can do use easting/northing offsets reported by GPS.
        easting, northing, zone_num, zone_letter = utm.from_latlon(self.ggk['latitude'], self.ggk['longitude'])

        # Take into account the fact the platform center is in between the two antennas and the
        # reported lat/lon is only for the primary receiver (which we mount on the right)
        ant1_offset = self.avr['range'] / 2.0 # antenna 1 offset in meters
        east_antenna_offset = -math.sin(corrected_yaw) * ant1_offset
        north_antenna_offset = math.cos(corrected_yaw) * ant1_offset
        easting += east_antenna_offset
        northing += north_antenna_offset
        
        # Convert easting/northing back to lat/long since that's what needs to be uploaded to database.

        # Find altitude of center of antennas.  We don't know pitch so hopefully this is close enough.
        tilt_rad = self.avr['tilt_deg'] * deg2rad
        altitude_offset = math.sin(tilt_rad) * self.avr['range'] / 2.0
        corrected_altitude = self.ggk['altitude'] - altitude_offset
        
        corrected_lat, corrected_long = utm.to_latlon(easting, northing, zone_num, zone_letter)
    
        # Monitor fix type.
        fix = str(self.ggk['gps_quality'])

        if self.required_fix != 'none' and fix != self.required_fix:
            if fix != self.last_fix:
                self.send_text('Insufficient fix: {} ({})'.format(self.ggk_fix_types[fix], fix))
            self.last_fix = fix
            data_quality_ok = False
            
        elif fix != self.last_fix:  # fix is ok so just tell user once 
            self.send_text('Current fix: {} ({})'.format(self.ggk_fix_types[fix], fix))
             
        self.last_fix = fix
    
        # Monitor number of satellites.
        num_sats = self.ggk['sats_used']
        enough_satellites = num_sats >= self.min_sats
        
        if not enough_satellites:
            if self.enough_satellites_last_message:
                self.send_text('Not enough satellites.')
            self.enough_satellites_last_message = enough_satellites
            data_quality_ok = False
        
        if self.min_sats > 0 and enough_satellites and not self.enough_satellites_last_message:
            self.send_text('Tracking enough satellites.')
            
        self.enough_satellites_last_message = enough_satellites
        
        if utc_override:
            utc_time = utc_override
            # Override data quality because this is only used for test GPS to make sure first time stamp
            # is unique, so need to make sure the over-ridden UTC time is actually used.
            data_quality_ok = True
             
        self.handle_data(utc_time, sys_time, [corrected_lat, corrected_long, corrected_altitude, corrected_yaw * rad2deg,
                                               num_sats, self.ggk['dop']], data_quality_ok)
        
        return 'normal' if data_quality_ok else 'bad_data_quality'
                                                        
    def handle_avr_message(self, data):

        self.avr_count += 1
        
        self.avr = data

        return True # processed successfully
        
    def handle_ggk_message(self, data):

        self.ggk_count += 1

        self.ggk = data

        if self.ggk['latitude_direction'] == 'S':
            self.ggk['latitude'] *= -1

        if self.ggk['longitude_direction'] == 'W':
            self.ggk['longitude'] *= -1

        # Strip off EHT prefix and convert to float
        try:
            altitude = self.ggk['height_above_ellipsoid']
            altitude = float(altitude[3:])
        except ValueError:
            return False # not processed successfully.
        
        self.ggk['altitude'] = altitude

        return True # processed successfully
    
    def log_next_position_with_notes(self, notes):
        
        self.log_next_position = True
        self.next_log_notes = notes
        

