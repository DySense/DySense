# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import yaml
import os
import logging

from dysense.core.version import *
    
def save_config_file(presenter, file_path):
    '''Write current controller/sensors out to specified file path so the user can reload it later.'''
    # Data is what gets dumped to the file using yaml.
    data = {}
   
    controllers = []
    for controller_id, controller_info in presenter.controllers.iteritems():
        # TODO support multiple controllers
        useful_info = {}
        for info_name, info_value in controller_info.iteritems():
            if info_name in ['settings', 'time_source', 'position_sources', 'orientation_sources', 'height_sources', 'fixed_height_source']:
                useful_info[info_name] = info_value
        controllers.append(useful_info)
    data['controllers'] = controllers

    sensors = []
    for (sensor_id, controller_id), sensor_info in presenter.sensors.iteritems():
        # TODO save sensors in consistent order
        # TODO save sensors underneath controllers?
        useful_info = {}
        for info_name, info_value in sensor_info.iteritems():
            if info_name in ['sensor_type', 'sensor_id', 'settings', 'position_offsets', 'orientation_offsets', 'instrument_type', 'instrument_tag']:
                useful_info[info_name] = info_value
        sensors.append(useful_info)
    data['sensors'] = sensors
    
    # Save version number when config was saved for detecting issues when loading config on a different version.        
    data['app_version'] = app_version

    with open(file_path, 'w') as outfile:
        outfile.write(yaml.safe_dump(data, allow_unicode=True, default_flow_style=False))
    
def load_config_file(presenter, file_path):
    '''Load controller/sensors out of specified yaml file path.'''
        
    if not os.path.exists(file_path):
        presenter.new_error_message("Config file '{}' does not exist.".format(file_path), logging.ERROR)
        return
    
    # TODO support multiple controllers
    if len(presenter.controllers) == 0:
        presenter.new_error_message("Need at least one controller before loading config", logging.ERROR)
        return
    
    # TODO update for multiple controllers
    if presenter.local_controller['session_active']:
        presenter.invalid_command_during_session('load config')
        return
    
    # TODO remove other controllers (and their sensors?) once that's all supported
    presenter.remove_all_sensors(only_on_active_controller=True)
        
    with open(file_path, 'r') as stream:
        data = yaml.load(stream)
    
    # Request that all data stored in saved controller info gets set to the active controller (which right now is the only allowed controller)
    for saved_controller_info in data.get('controllers', []):
        for info_name, info_value in saved_controller_info.iteritems():
            if info_name == 'settings':
                for setting_name, setting_value in info_value.iteritems():
                    presenter.change_controller_setting(setting_name, setting_value)
            elif info_name == 'version':
                pass # TODO verify program version matches config version
            else:
                presenter.change_controller_info(info_name, info_value) 
                
    # Request that all saved sensors get added to the active controller (which right now is the only allowed controller)
    for saved_sensor_info in data.get('sensors', []):
        presenter.add_sensor(saved_sensor_info)