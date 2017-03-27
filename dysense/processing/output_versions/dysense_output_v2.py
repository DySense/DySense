# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import copy
from collections import defaultdict

from dysense.core.utility import yaml_load_unicode, validate_type
from dysense.processing.utility import unicode_csv_reader
from dysense.processing.utility import StampedAngle, StampedPosition, StampedHeight
from dysense.processing.log import log

class SessionOutputV2(object):
    '''
    Provide interface for reading different parts of a DySense session directory.
    Before using data user should verify that session_valid property is True.
    All files are assumed to be saved in UTF8 format.
    '''
    def __init__(self, session_path, version):
        '''Constructor'''
        self.session_path = session_path
        self.version = version

        self.sources = self._read_data_source_info()

        self.sensor_info_list = self._read_sensor_info()

        # Associate (sensor_id, controller_id) to the data stored in that sensor log.
        # Keeping this map lets us avoid reading the same log in multiple times.
        self.sensor_to_data = {}

    @property
    def session_info_file_path(self):
        return os.path.join(self.session_path, 'session_info.csv')

    @property
    def source_info_file_path(self):
        return os.path.join(self.session_path, 'source_info.yaml')

    @property
    def sensor_info_directory_path(self):
        return os.path.join(self.session_path, 'sensor_info/')

    @property
    def data_logs_directory_path(self):
        return os.path.join(self.session_path, 'data_logs/')

    @property
    def data_files_directory_path(self):
        return os.path.join(self.session_path, 'data_files/')

    @property
    def time_source(self):
        return self.sources.get('time_source', None)

    @property
    def position_sources(self):
        return self.sources.get('position_sources', [])

    @property
    def position_sources_info(self):
        return [self.find_matching_sensor_info(source) for source in self.position_sources]

    @property
    def roll_source(self):
        return self.sources.get('roll_source', None)

    @property
    def pitch_source(self):
        return self.sources.get('pitch_source', None)

    @property
    def yaw_source(self):
        return self.sources.get('yaw_source', None)

    @property
    def height_sources(self):
        return self.sources.get('height_sources', [])

    @property
    def fixed_height_source(self):
        return self.sources.get('fixed_height_source', None)

    @property
    def session_valid(self):
        return not os.path.exists(os.path.join(self.session_path, 'invalidated.txt'))

    def read_positions(self):
        '''
        Read time-stamped position information from position sensor logs.

        Return dictionary of position sources where each key is the position source name and
         the value is a list of StampedPosition objects sorted by time.

        If there are any issues getting data from a position source will raise ValueError
        '''
        # Make sure there is a valid position source.
        if len(self.position_sources) == 0:
            raise ValueError('No valid position sources found in session metadata.')

        # Dictionary that will be returned at end of method.
        measurements_by_source = defaultdict(list)

        for position_source in self.position_sources:

            position_source_name = position_source['sensor_id']

            matching_sensor_info = self.find_matching_sensor_info(position_source)

            sensor_log_data, _ = self._read_sensor_log_data(matching_sensor_info)

            if sensor_log_data is None:
                raise ValueError('Position sensor {} does not have any log data'.format(position_source_name))

            for data_entry in sensor_log_data:

                utc_time = data_entry['time']
                data = data_entry['data']
                lat = float(data[position_source['x_index']])
                long = float(data[position_source['y_index']])
                alt = float(data[position_source['z_index']])

                new_position = StampedPosition(utc_time, lat, long, alt)

                measurements_by_source[position_source_name].append(new_position)

        # Data is already sorted by time-stamp.

        return measurements_by_source

    def read_orientations(self):
        '''
        Read time-stamped angles from the sensor logs specified by orientation sources.

        Return value will be roll, pitch, yaw where each of these may be 3 different things:
            1) None if that source (e.g. pitch source) wasn't specified for session.
            2) The string 'derived' if the angles should be calculated (e.g. using multiple-accurate position sources)
            3) A list of TimeStampedAngles sorted by time.
        '''
        roll_values = self._read_angle(self.roll_source)
        pitch_values = self._read_angle(self.pitch_source)
        yaw_values = self._read_angle(self.yaw_source)

        return roll_values, pitch_values, yaw_values

    def read_heights_above_ground(self):
        '''
        Read time-stamped height information from height sensor logs.

        Return dictionary of height sources where each key is the height source name and
         the value is a list of StampedHeight objects sorted by time.

        If there are any issues getting data from a height source will raise ValueError
        '''
        # Dictionary that will be returned at end of method.
        measurements_by_source = defaultdict(list)

        for height_source in self.height_sources:

            height_source_name = height_source['sensor_id']

            matching_sensor_info = self.find_matching_sensor_info(height_source)

            sensor_log_data, _ = self._read_sensor_log_data(matching_sensor_info)

            if sensor_log_data is None:
                raise ValueError('Height sensor {} does not have any log data'.format(height_source_name))

            for data_entry in sensor_log_data:

                utc_time = data_entry['time']
                data = data_entry['data']
                height_measurement = float(data[height_source['height_index']])

                new_height = StampedHeight(utc_time, height_measurement)

                measurements_by_source[height_source_name].append(new_height)

        # Data is already sorted by time-stamp.

        return measurements_by_source

    def read_fixed_height_above_ground(self):
        '''Return fixed distance above ground in meters.'''

        return self.fixed_height_source.get('height', None)

    def get_complete_sensors(self):

        # Initialize sensors with information from sensor info yaml files.
        sensors = copy.deepcopy(self.sensor_info_list)

        # Combine log data with sensor info.
        for sensor in sensors:
            try:
                log_data, log_file_name = self._read_sensor_log_data(sensor)

            except Exception as e:
                log().error('Cannot read log for {} - reason: {}'.format(sensor['sensor_id'], str(e)))
                log_data = None
                log_file_name = None

            sensor['log_data'] = log_data
            sensor['log_file_name'] = log_file_name

        return sensors

    def read_session_info(self):

        session_info = {}
        with open(self.session_info_file_path, 'r') as session_info_file:
            file_reader = unicode_csv_reader(session_info_file)
            for line_num, line in enumerate(file_reader):

                if len(line) == 0 or line[0].strip().startswith('#'):
                    continue # blank or comment line

                info_name = line[0]
                try:
                    info_value = line[1]
                except IndexError:
                    info_value = None

                # Convert information that should be floats.
                if info_name in ['start_utc', 'end_utc', 'start_sys_time', 'end_sys_time']:
                    info_value = float(info_value)

                # Convert information that should be boolean.
                if info_name in ['surveyed']:
                    info_value = bool(info_value)

                session_info[info_name] = info_value

        return session_info

    def find_matching_sensor_info_by_name(self, source_sensor_id):

        # TODO update for multiple controllers
        matching_sensors = [s for s in self.sensor_info_list if s['sensor_id'] == source_sensor_id]

        if len(matching_sensors) > 1:
            raise ValueError('More than 1 sensor found named {} with same controller ID {}'.format(source_sensor_id, 'TODO'))
        elif len(matching_sensors) == 0:
            raise ValueError('More than 1 sensor found named {} with same controller ID {}'.format(source_sensor_id, 'TODO'))

        return matching_sensors[0]

    def find_matching_sensor_info(self, source):

        return self.find_matching_sensor_info_by_name(source['sensor_id'])

    def find_matching_height_source(self, source_name):

        return [s for s in self.height_sources if source_name == s['sensor_id']][0]

    def _read_data_source_info(self):

        with open(self.source_info_file_path, 'r') as stream:
            return yaml_load_unicode(stream)

    def _read_sensor_info(self):

        sensor_info_list = []
        for file_name in os.listdir(self.sensor_info_directory_path):
            extension = os.path.splitext(file_name)[1]
            if 'yaml' not in extension:
                continue

            file_path = os.path.join(self.sensor_info_directory_path, file_name)
            with open(file_path, 'r') as stream:
                sensor_info = yaml_load_unicode(stream)

            sensor_info_list.append(sensor_info)

        return sensor_info_list

    def _read_sensor_log_data(self, sensor_info):
        ''''''

        # The beginning part of the filename that we expect based on provided sensor info.
        log_file_name_start = '{}_{}_{}'.format(sensor_info['sensor_id'], sensor_info['instrument_type'], sensor_info['instrument_tag'])

        matching_file_names = []
        for fname in os.listdir(self.data_logs_directory_path):
            file_name_without_ext, extension = os.path.splitext(fname)
            if log_file_name_start in fname and 'csv' in extension:
                matching_file_names.append(fname)

        if len(matching_file_names) == 0:
            raise Exception("No matching log starting with {}".format(log_file_name_start))
        elif len(matching_file_names) > 1:
            raise Exception("More than one log starting with {}".format(log_file_name_start))
        else:
            matching_file_name = matching_file_names[0]

        full_id = (sensor_info['sensor_id'], sensor_info['controller_id'])

        if full_id in self.sensor_to_data:
            # Data has already been read in earlier, so don't do it again.
            sensor_log_data = self.sensor_to_data[full_id]
            return sensor_log_data, matching_file_name

        # Look up what types line up which pieces of data.
        if sensor_info['metadata'] is None:
            raise Exception("Cannot convert sensor data since no metadata could be found.")

        conversion_types = [setting_metadata['type'] for setting_metadata in sensor_info['metadata']['data']]

        file_path = os.path.join(self.data_logs_directory_path, matching_file_name)

        sensor_log_data = []
        with open(file_path, 'rb') as log_file:
            file_reader = unicode_csv_reader(log_file)
            for line_num, line in enumerate(file_reader):

                if len(line) == 0:
                    continue # blank

                # UTC time is always first column.
                time_entry = line[0].strip()

                if time_entry == "" or time_entry.startswith('#'):
                    continue # invalid or comment line

                utc_time = float(time_entry)

                log_data_entry = line[1:]

                # Convert each piece of data to the correct type.
                for element_idx, element_value in enumerate(log_data_entry):
                    try:
                        log_data_entry[element_idx] = validate_type(element_value, conversion_types[element_idx])
                    except ValueError:
                        raise ValueError("{} cannot be converted into the expected type '{}'".format(element_value, conversion_types[element_idx]))

                sensor_log_data.append({'time': utc_time, 'data': log_data_entry})

        # Sort data by time stamp.
        sensor_log_data = sorted(sensor_log_data, key=lambda data: data['time'])

        # Save data to avoid reading it in again.
        self.sensor_to_data[full_id] = sensor_log_data

        return sensor_log_data, matching_file_name

    def _read_angle(self, source):

        if not source or source['sensor_id'].lower() == 'none':
            return None
        elif source['sensor_id'].lower() == 'derived':
            return 'derived'

        matching_sensor_info = self.find_matching_sensor_info(source)

        sensor_log_data, _ = self._read_sensor_log_data(matching_sensor_info)

        measurements = []

        for data_entry in sensor_log_data:

            utc_time = data_entry['time'] # utc time is standardized as first element
            angle_value = float(data_entry['data'][source['orientation_index']])

            measurements.append(StampedAngle(utc_time, angle_value))

        # Angles already sorted by time.
        return measurements

def _matches_source(sensor, source):

    return sensor['sensor_id'] == source['sensor_id'] and sensor['controller_id'] == source['controller_id']

