# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import math
import csv

from dysense.sensors.gps.nmea_parser import parse_nmea_sentence
from dysense.sensors.gps.checksum_utils import check_nmea_checksum
from dysense.sensor_base.sensor_base import SensorBase
from dysense.core.utility import utf_8_encoder

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

        # Set below based on which message is processed.  Default to last state in case it's not updated.
        current_state = self.last_state

        if 'AVR' == sentence_type:
            processed_successfully = self.handle_avr_message(parsed_sentence)
            if not processed_successfully:
                current_state = 'error'

        elif 'GGK' == sentence_type:
            processed_successfully = self.handle_ggk_message(parsed_sentence)
            if processed_successfully:
                current_state = self.combine_position_and_orientation(self.ggk['utc_time'], message_read_sys_time)

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
            # Should be receiving both types of messages by now...
            current_state = 'timed_out'

        self.last_state = current_state

        self._write_raw_string_to_file(nmea_string)

        return current_state

    def combine_position_and_orientation(self, utc_time, sys_time):

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

        # Cap corrected yaw between +/- PI
        while corrected_yaw > +math.pi: corrected_yaw -= 2 * math.pi
        while corrected_yaw < -math.pi: corrected_yaw += 2 * math.pi

        # Convert platform lat/long to NED (in meters) so we can add in secondary antenna offsets reported by GPS.
        # This uses a linear approximation which changes based on the reference latitude.
        # See: https://en.wikipedia.org/wiki/Geographic_coordinate_system#Expressing_latitude_and_longitude_as_linear_units
        lat_ref = self.ggk['latitude'] * deg2rad
        meters_per_deg_lat = 111132.92 - 559.82*math.cos(2.0*lat_ref) + 1.175*math.cos(4.0*lat_ref) - 0.0023*math.cos(6.0*lat_ref)
        meters_per_deg_long = 111412.84*math.cos(lat_ref) - 93.5*math.cos(3.0*lat_ref) + 0.118*math.cos(5.0*lat_ref)

        # These northing/easting are not geodetically meaningful (in an accuracy sense),
        # since the linear approximation only applies to this degree of latitude, not all degrees..
        # but that's ok since we're just dealing with small offsets.
        northing = self.ggk['latitude'] * meters_per_deg_lat
        easting = self.ggk['longitude'] * meters_per_deg_long

        # Take into account the fact the platform center is in between the two antennas and the
        # reported lat/lon is only for the primary receiver (which we mount on the right)
        ant1_offset = self.avr['range'] / 2.0 # antenna 1 offset in meters
        north_antenna_offset = math.sin(corrected_yaw) * ant1_offset
        east_antenna_offset = -math.cos(corrected_yaw) * ant1_offset

        northing += north_antenna_offset
        easting += east_antenna_offset

        # Find altitude of center of antennas.  We don't know pitch so hopefully this is close enough.
        tilt_rad = self.avr['tilt_deg'] * deg2rad
        altitude_offset = math.sin(tilt_rad) * ant1_offset
        corrected_altitude = self.ggk['altitude'] - altitude_offset

        # Convert northing/easting back to lat/long since that's what the standard for DySense.
        corrected_lat = northing / meters_per_deg_lat
        corrected_long = easting / meters_per_deg_long

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

        self.handle_data(utc_time, sys_time, [corrected_lat, corrected_long, corrected_altitude, corrected_yaw * rad2deg,
                                               num_sats, self.ggk['dop'], self.avr['tilt_deg']], data_quality_ok)

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

        # Altitude is above ellipsoid
        self.ggk['altitude'] = altitude

        return True # processed successfully

    def log_next_position_with_notes(self, notes):

        self.log_next_position = True
        self.next_log_notes = notes

    def close(self):
        '''Should be called when driver closes.'''

        self.close_open_files()

    def close_open_files(self):
        '''Close any file handles that are open.'''

        if self.raw_nmea_out_file is not None:
            self.raw_nmea_out_file.close()
            self.raw_nmea_out_file = None

    def driver_handle_new_setting(self, setting_name, setting_value):
        '''Update settings to match new output data file directory.'''

        if setting_name == 'data_file_directory':
            output_directory = setting_value

            if not output_directory:
                self.close_open_files()
                return # wait until we have a valid session again.

            if self.last_data_file_directory != output_directory:
                # Output directory changed so make sure it exists.
                if not os.path.exists(output_directory):
                    os.makedirs(output_directory)

                self.last_data_file_directory = output_directory

                # Close old file so we can open a new one at the new path.
                self.close_open_files()

                raw_nmea_out_file_path = os.path.join(output_directory, 'raw_nmea_output.txt')
                self.raw_nmea_out_file = open(raw_nmea_out_file_path, 'w')

    def _write_raw_string_to_file(self, nmea_string):

        if self.raw_nmea_out_file is not None:
            self.raw_nmea_out_file.write(nmea_string + b'\n')


