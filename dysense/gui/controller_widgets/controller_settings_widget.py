# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from PyQt4.Qt import *
from PyQt4 import QtGui, QtCore

from dysense.core.utility import make_unicode, pretty

class ControllerSettingsWidget(QWidget):
    
    def __init__(self, presenter, controller_info, only_basic_settings=False, *args):
        QWidget.__init__(self, *args)
        
        self.presenter = presenter
        self.controller_id = controller_info['id']
        controller_settings = controller_info['settings']
        self.only_basic_settings = only_basic_settings
        
        # Populated from controller settings to relate widgets and settings.
        self.setting_name_to_object = {}
        self.object_to_setting_name = {}
        
        # Add Controller ID to list of settings so it gets generated on the widget.
        controller_settings['id'] = self.controller_id
        
        self.setup_ui(controller_settings)

    def setup_ui(self, controller_settings):
        
        self.main_layout = QGridLayout(self)
        
        # Override certain settings so they show something different for the text label.
        # (e.g. replace 'id' with 'controller id' since it's more descriptive for the user to see)
        settings_name_override = {'id': 'Controller ID',
                                  'base_out_directory': 'Output Folder',
                                  'experiment_id': 'Experiment ID'}
        
        # Define what order settings will show up in widget.
        settings_order = ['id', 'base_out_directory', 'operator_name', 'platform_type', 'platform_tag', 'experiment_id', 'surveyed']
        
        setting_name_to_tooltip = {'id': 'Name of this computer. Should be unique.',
                                   'base_out_directory': 'Base folder where new session folders will be saved.',
                                   'operator_name': 'First and last name of person in charge of session.',
                                   'platform_type': 'Name associated with this type of platform.',
                                   'platform_tag': 'Unique ID of platform (e.g. serial number)',
                                   'experiment_id': 'ID of experiment being covered by this session.',
                                   'surveyed': 'If using RTK then set to False if base station location is not surveyed. If not using RTK then always set to True',
                                   }
        
        # Convert settings to an ordered list so they show up in a consistent order.
        ordered_controller_settings = []
        for ordered_name in settings_order:
            try:
                setting_value = controller_settings[ordered_name]
            except KeyError:
                continue # setting not available.
                
            ordered_controller_settings.append((ordered_name, setting_value))
        
        for i, (setting_name, setting_value) in enumerate(ordered_controller_settings):
        
            if self.only_basic_settings and setting_name in ['id', 'base_out_directory']:
                continue # don't include this setting
        
            # Check if we need to replace setting name with something different.
            if setting_name in settings_name_override:
                display_name = settings_name_override[setting_name]
            else:
                display_name = pretty(setting_name)
            
            text_label = QLabel(display_name)
            value_line_edit = QLineEdit(make_unicode(setting_value))
            #text_label.setFont(self.w_font)
            #value_line_edit.setFont(self.dialog_font)
            
            tooltip = setting_name_to_tooltip.get(setting_name,'')
            text_label.setToolTip(tooltip)
            value_line_edit.setToolTip(tooltip)
            
            self.main_layout.addWidget(text_label, i, 0)
            self.main_layout.addWidget(value_line_edit, i, 1)
            
            self.object_to_setting_name[value_line_edit] = setting_name
            self.setting_name_to_object[setting_name] = value_line_edit
            
            # Connect signal so we know when value changes
            value_line_edit.editingFinished.connect(self.value_changed_by_user)
            
        
        
    def value_changed_by_user(self):
        
        # Only run method if value was actually changed.
        if not self.sender().isModified():
            return
        self.sender().setModified(False)
        
        new_setting_value = self.sender().text()
        setting_name = self.object_to_setting_name[self.sender()]        
        
        if setting_name == 'id':
            # Controller ID isn't technically a setting so handle it differently.
            self.presenter.controller_name_changed(new_setting_value)
        else:
            self.presenter.change_controller_setting(setting_name, new_setting_value) 
        
    def update_setting(self, setting_name, setting_value):

        matching_line_edit = self.setting_name_to_object[setting_name]

        matching_line_edit.setText(make_unicode(setting_value))
        
    '''
    def output_directory_tool_button_clicked(self):
        output_directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        
        if not output_directory:
            return # User didn't select a directory.
        
        self.output_directory_line_edit.setText(output_directory)
        self.output_directory_line_edit.setModified(True)
        self.output_directory_line_edit.editingFinished.emit()
    '''