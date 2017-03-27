# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time

from dysense.core.sensor_creation import SensorCloseTimeout
from dysense.core.utility import validate_setting, validate_type, pretty, make_unicode
from dysense.interfaces.component_connection import ComponentConnection

class SensorConnection(ComponentConnection):

    def __init__(self, interface, version, sensor_id, controller_id, sensor_type, settings, position_offsets,
                 orientation_offsets, instrument_type, instrument_tag, metadata, controller, driver_factory):
        '''Constructor'''

        super(SensorConnection, self).__init__(interface, sensor_id)

        self.version = version
        self.sensor_id = sensor_id # same as sensor name
        self.controller_id = controller_id
        self._sensor_type = sensor_type
        self._settings = settings
        self.metadata = metadata

        self._sensor_state = 'closed'
        self._sensor_health = 'neutral'
        self._sensor_paused = True

        self.overall_health = 'neutral'

        self.text_messages = []

        # Sensor offsets relative to vehicle position.
        self._position_offsets = position_offsets # Forward right down - meters
        self._orientation_offsets = orientation_offsets # Roll pitch yaw - degrees

        # ID of the sensor itself, not the one assigned by the program.
        self._instrument_type = instrument_type
        self._instrument_tag = instrument_tag

        # Where to save data files (e.g. images) to. Only valid when session is active.
        self._desired_data_file_path = None

        # Either thread or process object that sensor driver runs in.
        self.sensor_driver = None

        # Notified when one of the public sensor fields change.
        self.controller = controller

        # Used to create new sensors.
        self.driver_factory = driver_factory

    @property
    def public_info(self):

        return {'sensor_id': self.sensor_id,
                'controller_id': self.controller_id,
                'sensor_type': self.sensor_type,
                'settings': self._settings,
                'connection_state': self._connection_state,
                'connection_health': self._connection_health,
                'sensor_state': self.sensor_state,
                'sensor_health': self.sensor_health,
                'sensor_paused': self.sensor_paused,
                'overall_health': self.overall_health,
                'text_messages': self.text_messages,
                'position_offsets': self.position_offsets,
                'orientation_offsets': self.orientation_offsets,
                'instrument_type': self.instrument_type,
                'instrument_tag': self.instrument_tag,
                'metadata': self.metadata
                }

    @property
    def instrument_id(self):
        return '{}_{}'.format(self.instrument_type, self.instrument_tag)

    @property
    def sensor_type(self):
        return self._sensor_type
    @sensor_type.setter
    def sensor_type(self, new_value):
        self._sensor_type = new_value
        self.notify_controller('sensor_type', self._sensor_type)

    @property
    def sensor_state(self):
        return self._sensor_state
    @sensor_state.setter
    def sensor_state(self, new_value):
        self._sensor_state = new_value
        self.notify_controller('sensor_state', self._sensor_state)

    @property
    def sensor_health(self):
        return self._sensor_health
    @sensor_health.setter
    def sensor_health(self, new_value):
        self._sensor_health = new_value
        self.notify_controller('sensor_health', self._sensor_health)
        self.update_overall_health()

    @property
    def sensor_paused(self):
        return self._sensor_paused
    @sensor_paused.setter
    def sensor_paused(self, new_value):
        self._sensor_paused = new_value
        self.notify_controller('sensor_paused', self._sensor_paused)

    @property
    def position_offsets(self):
        return self._position_offsets
    @position_offsets.setter
    def position_offsets(self, new_value):
        validated_offsets = []
        for offset in new_value:
            validated_offsets.append(validate_type(offset, 'float'))
        self._position_offsets = validated_offsets
        self.notify_controller('position_offsets', self._position_offsets)

    @property
    def orientation_offsets(self):
        return self._orientation_offsets
    @orientation_offsets.setter
    def orientation_offsets(self, new_value):
        validated_offsets = []
        for offset in new_value:
            validated_offsets.append(validate_type(offset, 'float'))
        self._orientation_offsets = validated_offsets
        self.notify_controller('orientation_offsets', self._orientation_offsets)

    @property
    def instrument_type(self):
        return self._instrument_type
    @instrument_type.setter
    def instrument_type(self, new_value):
        self._instrument_type = new_value
        self.notify_controller('instrument_type', self._instrument_type)

    @property
    def instrument_tag(self):
        return self._instrument_tag
    @instrument_tag.setter
    def instrument_tag(self, new_value):
        self._instrument_tag = new_value
        self.notify_controller('instrument_tag', self._instrument_tag)

    def notify_controller(self, info_name, new_info_value):
        self.controller.notify_sensor_changed(self.sensor_id, info_name, new_info_value)

    def update_setting(self, setting_name, new_value):

        setting_metadata = [s for s in self.metadata['settings'] if s['name'] == setting_name][0]

        new_value = validate_setting(new_value, setting_metadata)

        self._settings[setting_name] = new_value

        self.notify_controller('settings', self._settings)

        self.send_message('change_setting', (setting_name, new_value))

    def validate_settings(self):

        for setting_name, setting_value in self._settings.items():
            self.update_setting(setting_name, setting_value)

    def connection_state_changed(self, new_state):
        '''Called from parent Connection class whenever state changes.'''

        # Auto close if connection state closes or goes bad.
        if new_state in ['closed', 'error', 'timed_out'] and not self.is_closed():
            self.close()

        self.notify_controller('connection_state', self._connection_state)
        self.notify_controller('connection_health', self._connection_health)
        self.update_overall_health()

        if self._connection_state == 'opened':
            # Update any session-dependent settings that were lost when sensor was closed.
            self.update_data_file_directory(self._desired_data_file_path)

        # Show user (and log) changes in connection state.  Don't show opened since printing two
        # messages is obnoxious.  If it's not opened then it will throw an error or timeout.
        if new_state != 'opened':
            self.controller.handle_new_sensor_text(self, 'Driver {}'.format(pretty(new_state)))

    def update_overall_health(self):

        if self._connection_health == 'bad' or self.sensor_health == 'bad':
            self.overall_health = 'bad'
        elif self._connection_health == 'good' and self.sensor_health == 'good':
            self.overall_health = 'good'
        else:
            self.overall_health = 'neutral'
        self.notify_controller('overall_health', self.overall_health)

        # Make sure an issue is active if the health is bad.
        if self.overall_health == 'bad':
            if self._connection_health == 'bad' and self.sensor_health == 'bad':
                issue_reason = "Bad driver state '{}' and bad sensor state '{}'".format(self._connection_state, self.sensor_state)
            elif self._connection_health == 'bad':
                issue_reason = "Bad driver state '{}'".format(self._connection_state)
            else: # just sensor health is bad
                issue_reason = "Bad sensor state '{}'".format(self.sensor_state)

            self.controller.try_create_issue(self.controller.controller_id, self.sensor_id, 'unhealthy_sensor', issue_reason, 'error')
        else:
            # Resolve any possible old issues dealing with sensor health.
            self.controller.try_resolve_issue(self.sensor_id, 'unhealthy_sensor')

    def reset(self):
        '''Reset all fields that may have changed last time sensor was setup/running.'''

        ComponentConnection.reset(self)

        self.sensor_state ='closed'
        self.sensor_health = 'neutral'
        self.sensor_paused = True
        self.text_messages = []

    def setup(self):

        if self.sensor_driver:
            return # Need to call close() first before making a new sensor driver instance

        self.reset()

        try:
            self.sensor_driver = self.driver_factory.create_sensor(self.sensor_type, self.sensor_id, self.instrument_id, self._settings)
        except Exception as e:
            self.controller.handle_new_sensor_text(self, "{}".format(repr(e)))

        if self.sensor_driver:
            self.update_connection_state('setup')
        else:
            self.update_connection_state('error')

    def close(self):
        '''Close down process or thread associated with connection.  Need to send close message before calling this.'''

        self.send_command('close')

        try:
            if self.sensor_driver:
                self.sensor_driver.close(timeout=3) # TODO allow sensor driver to specify timeout
                self.sensor_driver = None
            else:
                # There's no driver to close down.  Most likely this is the user hitting close after there's been an error
                # so just reset the driver state since the user is essentially 'acknowledging' they say what was wrong.
                self.sensor_state = 'closed'
                self.sensor_health = 'neutral'
                self.sensor_paused = True
        except SensorCloseTimeout:
            pass # TODO notify that sensor didn't close down in required time

        ComponentConnection.close(self)

    def is_closed(self):
        '''Return true if sensor driver is closed.'''
        return self.sensor_driver is None

    def update_data_file_directory(self, new_directory_path):

        self._desired_data_file_path = new_directory_path
        self.send_message('change_setting', ('data_file_directory', new_directory_path))

    def send_time(self, new_time):

        self.send_message('time', new_time)

    def send_command(self, command_name, command_args=None):

        self.send_message('command', (command_name, command_args))
