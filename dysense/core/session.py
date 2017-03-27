# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import logging
import os
import datetime

from dysense.core.utility import make_filename_unique
from dysense.core.csv_log import CSVLog

class Session(object):

    def __init__(self, controller):

        self.controller = controller

        self._active = False
        self._name = 'N/A'
        self._path = "None"
        self._state = 'closed'

        self.notes = None

        # If set to true then session state will be 'paused' instead of 'started'
        # when session is resumed after all issues are cleared.
        self.pause_on_resume = True

        # Set to true if session is invalidated.
        self.invalidated = False

        # Start times associated with session, or if a session isn't active then will be from the last session.
        self.start_utc = 0.0
        self.start_sys_time = 0.0

    @property
    def state(self):
        return self._state
    @state.setter
    def state(self, new_value):
        self._state = new_value
        self.notify_controller('state', new_value)

    @property
    def active(self):
        return self._active
    @active.setter
    def active(self, new_value):

        if new_value == self._active:
            return # value not changed

        self._active = new_value
        self.notify_controller('active', new_value)

    @property
    def name(self):
        return self._name
    @name.setter
    def name(self, new_value):
        self._name = new_value
        self.notify_controller('name', new_value)

    @property
    def path(self):
        return self._path
    @path.setter
    def path(self, new_value):
        self._path = new_value
        self.notify_controller('path', new_value)

    def notify_controller(self, info_name, new_info_value):
        self.controller.notify_session_changed(info_name, new_info_value)

    def setup_logging(self):

        # Create logger to write out to a file.
        log = logging.getLogger("session")
        log.setLevel(logging.DEBUG)
        handler = logging.FileHandler(os.path.join(self.path, time.strftime("log.log")))
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s'))
        log.addHandler(handler)

    def close_logging(self):

        log = logging.getLogger('session')
        handlers = log.handlers[:]
        for handler in handlers:
            handler.close()
            log.removeHandler(handler)

    def update_state(self):

        if self.state == 'closed':
            return

        if self.state == 'waiting_for_time':
            seconds_since_last_utc_time = time.time() - self.controller.last_sys_time_update
            if seconds_since_last_utc_time < 3:
                self.start_sys_time = self.controller.last_sys_time_update
                self.start_utc = self.controller.last_utc_time
                self.state = 'waiting_for_position'

        if self.state == 'waiting_for_position':
            for source in self.controller.position_sources:
                if not source.receiving:
                    return
            # All sources receiving.
            self.state = 'waiting_for_orientation'

        if self.state == 'waiting_for_orientation':
            for source in self.controller.orientation_sources:
                if not source.receiving:
                    return
            # All sources receiving.
            self.state = 'waiting_for_height'

        if self.state == 'waiting_for_height':
            for source in self.controller.height_sources:
                if not source.receiving:
                    return
            # All sources receiving.
            self.state = 'starting'

        if self.state == 'starting':
            # Re-verify things in case they changed while waiting for data sources.
            if not self.controller.verify_controller_settings(manager=None):
                self.state = 'closed'
                return
            self.start()
            self.state = 'started'

        if self.state in ['started', 'paused']:
            for issue in self.controller.active_issues:
                if issue.level == 'critical':
                    self.state = 'suspended'

        if self.state == 'suspended':

            still_have_critical_issue = False
            for issue in self.controller.active_issues:
                if issue.level == 'critical':
                    still_have_critical_issue = True
                    break

            if still_have_critical_issue:
                # Make sure all sensors aren't saving data files because data isn't being logged.
                self.controller.send_command_to_all_sensors('pause')
            else:
                if self.pause_on_resume:
                    self.state = 'paused'
                else:
                    # Automatically resume session.
                    self.state = 'started'
                    self.controller.send_command_to_all_sensors('resume')

    def begin_startup_procedure(self, manager):

        # Make sure flag is cleared so that if session is (or will be) suspended that the session will automatically resume once issues are resolved.
        self.pause_on_resume = False

        if self.active:

            if self.state == 'suspended':
                self.log_message("Session is suspended because of a critical issue. Please resolve all issues and then session will resume automatically.", logging.ERROR, manager)
                return False

            if self.state == 'paused':
                self.state = 'started'
                self.log_message('Session resumed.', logging.INFO)

            # Already have a session started, so make sure all sensors are un-paused.
            self.controller.send_command_to_all_sensors('resume')

            return True # session already setup and in a good state so consider successful

        if not self.controller.verify_controller_settings(manager):
            return False

        if self.controller.time_source is None:
            self.log_message("Can't start session without a selected time source.", logging.ERROR, manager)
            return False

        if len(self.controller.position_sources) == 0:
            self.log_message("Can't start session without at least one selected position source.", logging.ERROR, manager)
            return False

        for source in self.controller.all_sources:
            if (source.controller_id.lower() not in ['none', 'derived']) and source.controller_id != self.controller.controller_id:
                self.log_message("Can't start session because source '{}' is part of a controller '{}' that's not connected.".format(source.sensor_id, source.controller_id), logging.ERROR, manager)
                return False

        for sensor in self.controller.sensors:
            if sensor.is_closed() or sensor.num_messages_received == 0:
                self.log_message("Can't start session until sensor '{}' is setup.".format(sensor.sensor_id), logging.ERROR, manager)
                return False

        self.log_message("Initial startup successful.")
        self.state = 'waiting_for_time'

        return True # initial startup successful

    def start(self):

        self.start_utc = self.controller.last_utc_time

        settings = self.controller.core_settings

        formatted_time = datetime.datetime.fromtimestamp(self.start_utc).strftime("%Y%m%d_%H%M%S")

        self.name = "{}_{}_{}".format(settings['platform_type'],
                                      settings['platform_tag'],
                                      formatted_time)

        self.name = make_filename_unique(settings['base_out_directory'], self.name)

        self.path = os.path.join(settings['base_out_directory'], self.name)

        self.active = True

        self.log_message("Session started.")

        # Go through and tell every sensor where to save it's data files.
        # Need to have each sensor have it's own sub-directory since some sensors (like the canon_edsdk)
        # won't work when multiple sensors are trying to write to the same directory.
        data_files_path = os.path.join(self.path, 'data_files/')
        for sensor in self.controller.sensors:
            sensor_data_file_directory = "{}_{}_{}".format(sensor.sensor_id, sensor.instrument_type, sensor.instrument_tag)
            sensor_data_file_path = os.path.join(data_files_path, sensor_data_file_directory)
            sensor.update_data_file_directory(sensor_data_file_path)

        data_logs_path = os.path.join(self.path, 'data_logs/')

        if not os.path.exists(data_logs_path):
            os.makedirs(data_logs_path)

        self.setup_logging()

        for sensor in self.controller.sensors:

            sensor_csv_file_name = "{}_{}_{}_{}.csv".format(sensor.sensor_id,
                                                            sensor.instrument_type,
                                                            sensor.instrument_tag,
                                                            formatted_time)

            sensor_csv_file_path = os.path.join(data_logs_path, sensor_csv_file_name)

            sensor.output_file = CSVLog(sensor_csv_file_path, buffer_size=1)

            # Store the names (e.g. latitude) of the sensor output data in the file.
            # The file will only be created once the sensor starts outputting data.
            sensor_data_names = [setting['name'] for setting in sensor.metadata['data']]
            sensor.output_file.handle_metadata(['utc_time'] + sensor_data_names)

        # Start all other sensors now that session is started.
        self.log_message("Starting all sensors.")
        self.controller.send_command_to_all_sensors('resume')

    def stop(self, interrupted):

        if not self.active:
            self.log_message("Session already closed.")
            self.state = 'closed' # make sure state is reset
            return # already closed

        self.controller.send_command_to_all_sensors('pause')

        for sensor in self.controller.sensors:
            sensor.output_file.terminate()

        # Go through and tell every sensor to stop saving data files to the current session.
        for sensor in self.controller.sensors:
            sensor.update_data_file_directory(None)

        self.close_logging()
        self.active = False
        self.state = 'closed'

        self.controller.write_session_file()
        self.controller.write_sensor_info_files()
        self.controller.write_data_source_info_files()

        if self.invalidated:
            # Create file to show that session is invalid.  Can't rename directory because sometimes we don't have permission to because
            # other files in the directory are still closing down, or the user has the directory open in an explorer window.
            invalidated_file_path = os.path.join(self.path, 'invalidated.txt')
            with open(invalidated_file_path, 'w') as invalidated_file:
                invalidated_file.write('The existence of this file means this session should not be uploaded to the database.')
            # Reset flag for next session.
            self.invalidated = False

        # Create file to show session wasn't closed by user.
        if interrupted:
            interrupted_file_path = os.path.join(self.path, 'interrupted.txt')
            with open(interrupted_file_path, 'w') as interrupted_file:
                interrupted_file.write('The existence of this file means the session was not closed by the user.  ' \
                                       'Either the program crashed or the user exited the application.  ' \
                                       'The data should still be valid.')

        self.notes = None

        self.log_message("Session closed.")

    def log_message(self, msg, level=logging.INFO, manager=None):

        self.controller.log_message(msg, level, manager)