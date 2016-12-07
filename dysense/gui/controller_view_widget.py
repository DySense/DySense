# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import logging

# TODO clean up imports
from PyQt4.QtGui import *
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QSize, QTimer

from dysense.gui.controller_view_widget_designer import Ui_controller_view
from dysense.core.utility import pretty, make_unicode, open_directory_in_viewer

# Controller dialogs
from dysense.gui.controller_dialogs.select_sources_dialog import SelectSourcesDialog
from dysense.gui.controller_dialogs.add_sensor_dialog import AddSensorDialog
from dysense.gui.controller_dialogs.end_session_dialog import EndSessionDialog
from dysense.gui.controller_dialogs.session_notes_dialog import SessionNotesDialog

# Stacked widgets
from dysense.gui.controller_widgets.controller_settings_widget import ControllerSettingsWidget
from dysense.gui.controller_widgets.controller_messages_widget import ControllerMessagesWidget
from dysense.gui.controller_widgets.controller_help_widget import ControllerHelpWidget
from dysense.gui.controller_widgets.controller_issues_widget import ControllerIssuesWidget

class ControllerViewWidget(QWidget, Ui_controller_view):
           
    def __init__(self, presenter, main_window, controller_id, controller_info, sensor_metadata):
  
        QWidget.__init__(self)
        
        # Call the auto-generated setupUi function in the designer file
        self.setupUi(self) 
        
        self.qt_settings = QtCore.QSettings("DySense", "ControllerView")
        
        self.presenter = presenter
        self.main_window = main_window
        self.controller_id = controller_id
        self.controller_info = controller_info
        self.sensor_metadata = sensor_metadata
        
        # Notes that have been saved by user for current session.
        self.session_notes = ""
        
        self.end_session_dialog = None # created when button is clicked
        
        # Setup widget
        self.load_session_icons()
        self.load_command_icons()
        self.load_stacked_widgets(presenter, controller_info)
        
        #self.resize_timer = QTimer()
        #self.resize_timer.setSingleShot(True)
        #self.resize_timer.timeout.connect(self.resize_command_icons)
        
        # Connect signals for main session buttons
        self.setup_sensors_button.clicked.connect(self.setup_sensors_button_clicked)
        self.start_button.clicked.connect(self.start_button_clicked)
        self.pause_button.clicked.connect(self.pause_button_clicked)
        self.notes_button.clicked.connect(self.notes_button_clicked)
        self.end_button.clicked.connect(self.end_button_clicked)
        
        # Connect signals for command buttons (left to right, top to bottom in grid)
        self.load_config_button.clicked.connect(self.load_config_button_clicked)
        self.load_last_config_button.clicked.connect(self.load_last_config_button_clicked)
        self.save_config_button.clicked.connect(self.save_config_button_clicked)
        self.add_sensor_button.clicked.connect(self.add_sensor_button_clicked)
        self.remove_sensors_button.clicked.connect(self.remove_sensors_button_clicked)
        self.select_sources_button.clicked.connect(self.select_sources_button_clicked)
        self.messages_button.clicked.connect(self.messages_button_clicked)
        self.issues_button.clicked.connect(self.issues_button_clicked)
        self.settings_button.clicked.connect(self.settings_button_clicked)
        self.add_controller_button.clicked.connect(self.add_controller_button_clicked)
        self.view_sensor_data_button.clicked.connect(self.view_sensor_data_button_clicked)
        self.help_button.clicked.connect(self.help_button_clicked)
        
    #-----------------------------------
    # Config file properties
    #-----------------------------------
    @property
    def last_saved_config_file_path(self):
        file_path = self.qt_settings.value("last_saved_config_file_path")
        if file_path is None:
            file_path = os.path.join(os.path.expanduser('~'), 'dysense_config.yaml')
        return make_unicode(file_path)
        
    @last_saved_config_file_path.setter
    def last_saved_config_file_path(self, new_value):
        self.qt_settings.setValue("last_saved_config_file_path", make_unicode(new_value))
      
    @property
    def last_loaded_config_file_path(self):
        file_path = self.qt_settings.value("last_loaded_config_file_path")
        return make_unicode(file_path)
        
    @last_loaded_config_file_path.setter
    def last_loaded_config_file_path(self, new_value):
        self.qt_settings.setValue("last_loaded_config_file_path", make_unicode(new_value))
        
    #-----------------------------------
    # Session button handlers
    #-----------------------------------
        
    def setup_sensors_button_clicked(self):
        self.presenter.setup_all_sensors(only_on_active_controller=True)
        
    def start_button_clicked(self):
        # If session is already started then controller will un-pause all sensors which is what we want.
        self.presenter.send_controller_command('start_session', send_to_all_controllers=False) 
        
    def pause_button_clicked(self):
        # If session isn't started then will still pause all sensors which is what we want.
        self.presenter.send_controller_command('pause_session', send_to_all_controllers=False) 

    def notes_button_clicked(self):
        self.notes_dialog = SessionNotesDialog(self, self.session_notes)
        self.notes_dialog.setModal(True)
        self.notes_dialog.show()
        
    def end_button_clicked(self):

        self.end_session_dialog = EndSessionDialog(self, self.presenter, self.controller_info, self.session_notes)
        self.end_session_dialog.setModal(True)
        self.end_session_dialog.show()
        #self.presenter.close_all_sensors(only_on_active_controller=True)
    
    #-----------------------------------
    # Command button handlers
    #-----------------------------------
    
    def load_config_button_clicked(self):
        
        config_file_path = QtGui.QFileDialog.getOpenFileName(self, 'Load Config', self.last_loaded_config_file_path, '*.yaml')
        if not config_file_path:
            return # User didn't select a config file.

        self.last_loaded_config_file_path = config_file_path
        
        # Also set this as the last saved so that when the user goes to save any updates
        # it defaults to this one.
        self.last_saved_config_file_path = config_file_path
        
        self.presenter.try_load_config(config_file_path)

    def load_last_config_button_clicked(self):

        self.presenter.try_load_config(self.last_loaded_config_file_path)

    def save_config_button_clicked(self):
        
        config_file_path = QtGui.QFileDialog.getSaveFileName(self, 'Save Config', self.last_saved_config_file_path, '*.yaml')

        if not config_file_path:
            return # User doesn't want to save the file.
        
        self.last_saved_config_file_path = config_file_path
        
        # Also set this as the last loaded so that when user opens the app again this will be default.
        self.last_loaded_config_file_path = config_file_path
        
        self.presenter.try_save_config(config_file_path)
    
    def add_sensor_button_clicked(self):
        
        possible_sensor_types = sorted(self.sensor_metadata.keys())
        sensor_id_types = [self.sensor_metadata[sensor_type]['type'] for sensor_type in possible_sensor_types]
        
        self.add_sensor_dialog = AddSensorDialog(self.presenter, possible_sensor_types, sensor_id_types)
        self.add_sensor_dialog.setModal(True)
        self.add_sensor_dialog.show()
    
    def remove_sensors_button_clicked(self):
        self.main_window.show_user_message('Select sensor in list and then press Remove button.', logging.INFO)
    
    def select_sources_button_clicked(self):

        self.select_sources_dialog = SelectSourcesDialog(self.presenter, self.controller_info, self.presenter.sensors)
        self.select_sources_dialog.setModal(True)
        self.select_sources_dialog.show()
    
    def messages_button_clicked(self):
        self.show_stacked_widget(self.messages_widget)
    
    def issues_button_clicked(self):
        self.show_stacked_widget(self.issues_widget)
    
    def settings_button_clicked(self):
        self.show_stacked_widget(self.settings_widget)
    
    def add_controller_button_clicked(self):
        self.main_window.show_user_message('Feature not supported in this release.', logging.INFO)
    
    def view_sensor_data_button_clicked(self):
        
        self.main_window.show_live_sensor_data()
    
    def help_button_clicked(self):
        self.show_stacked_widget(self.help_widget)
      
    #-----------------------------------
    # Update Methods
    #-----------------------------------
      
    def update_info(self, controller_info):
        
        self.controller_info = controller_info

        # Treat controller ID as a setting.
        self.settings_widget.update_setting('id', controller_info['id'])
                
        session_state = controller_info['session_state']
        if session_state.lower() == 'closed':
            session_status = 'Not Started'
        else:
            session_status = session_state
        self.session_status_label.setText(make_unicode(pretty(session_status)))

        settings = controller_info['settings'] 
        for setting_name, setting_value in settings.iteritems():               
            self.settings_widget.update_setting(setting_name, setting_value)
            if self.end_session_dialog is not None and self.end_session_dialog.isVisible():
                self.end_session_dialog.update_controller_setting(setting_name, setting_value)
                    
        extra_settings = controller_info['extra_settings']
        for setting_name, setting_value in extra_settings.iteritems():               
            self.settings_widget.update_setting(setting_name, setting_value)
            if self.end_session_dialog is not None and self.end_session_dialog.isVisible():
                self.end_session_dialog.update_controller_setting(setting_name, setting_value)
                    
    def update_session_notes(self, notes):
        
        self.session_notes = notes
        
    def add_message(self, message):
        
        self.messages_widget.append_message(message)
        
    def refresh_current_issues(self, current_issues):
        
        self.issues_widget.refresh_current_issues(current_issues)
        
    def extra_setting_added_or_removed(self, updated_extra_settings):
 
        self.settings_widget.setup_settings_frame(self.controller_info['settings'], updated_extra_settings)
        
    def clear_session_notes(self):
        self.session_notes = ""
      
    #-----------------------------------
    # Widget Methods
    #-----------------------------------

    def resizeEvent(self, event_info):
        
        self.resize_session_icons()
        self.resize_command_icons()

    def resize_session_icons(self):
        
        new_width = self.width()
        new_height = self.height()
        
        max_height = new_height * .18
        max_width = (new_width) / len(self.session_buttons)
        
        min_button_dimension = min(max_height, max_width)
        
        new_icon_width, new_icon_height = self.icon_size_for_button_size(min_button_dimension, self.session_buttons[0].font())
        
        # Keep a square
        new_icon_dimension = min(new_icon_height, new_icon_width)
        
        for session_button in self.session_buttons:

            session_button.setIconSize(QSize(new_icon_dimension, new_icon_dimension))
            
    def icon_size_for_button_size(self, min_button_dimension, font):
            
        icon_pad = min_button_dimension * .1
        text_height = QFontMetrics(font).height()
        
        icon_width = min_button_dimension - icon_pad
        icon_height = min_button_dimension - text_height

        return icon_width, icon_height
    
    def resize_command_icons(self):
        
        new_width = self.width() * .33
        new_height = self.height() * .5
        
        max_height = (new_height) / 4
        max_width = (new_width) / 3
        
        min_button_dimension = min(max_height, max_width)
        
        new_icon_width, new_icon_height = self.icon_size_for_button_size(min_button_dimension, self.command_buttons[0].font())
        
        # Keep a square
        new_icon_dimension = min(new_icon_height, new_icon_width)
        
        for command_button in self.command_buttons:
            
            #if new_icon_dimension < 30:
            #    command_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            #else:
            #    command_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            
            command_button.setIconSize(QSize(new_icon_dimension, new_icon_dimension))

    def load_session_icons(self):
        
        resources_directory = '../resources/session_icons'
        icon_file_name_to_button = {'setup_icon.png' : self.setup_sensors_button,
                                    'start_icon.png' : self.start_button,
                                    'pause_icon.png' : self.pause_button,
                                    'notes_icon.png' : self.notes_button,
                                    'end_icon.png' : self.end_button,
                                    }
        
        # Save list of session buttons so can update them as widget resizes.
        self.session_buttons = list(icon_file_name_to_button.values())
        
        for file_name, button in icon_file_name_to_button.iteritems():
            icon_path = os.path.join(resources_directory, file_name)
            icon = QtGui.QIcon(icon_path)
            button.setIcon(icon)
            
    def load_command_icons(self):
        
        resources_directory = '../resources/command_icons'
        icon_file_name_to_button = {'load_config_icon.png' : self.load_config_button,
                                    'load_last_config_icon.png' : self.load_last_config_button,
                                    'save_config_icon.png' : self.save_config_button,
                                    'add_sensor_icon.png' : self.add_sensor_button,
                                    'remove_sensor_icon.png' : self.remove_sensors_button,
                                    'select_sources_icon.png' : self.select_sources_button,
                                    'messages_icon.png' : self.messages_button,
                                    'issues_icon.png' : self.issues_button,
                                    'settings_icon.png' : self.settings_button,
                                    'add_controller_icon.png' : self.add_controller_button,
                                    'view_sensor_data_icon.png' : self.view_sensor_data_button,
                                    'help_icon.png' : self.help_button,
                                    }
        
        # Save list of session buttons so can update them as widget resizes.
        self.command_buttons = list(icon_file_name_to_button.values())
        
        for file_name, button in icon_file_name_to_button.iteritems():
            icon_path = os.path.join(resources_directory, file_name)
            icon = QtGui.QIcon(icon_path)
            button.setIcon(icon)
            
    def show_stacked_widget(self, widget_ref):
        
        widget_title = self.widget_titles[widget_ref]
        
        self.stacked_group_box.setTitle(make_unicode(widget_title))
        self.stacked_widget.setCurrentWidget(widget_ref)

    def load_stacked_widgets(self, presenter, controller_info):
        
        # Create widgets to go in stacked widget.
        self.settings_widget = ControllerSettingsWidget(presenter, controller_info)
        self.messages_widget = ControllerMessagesWidget()
        self.issues_widget = ControllerIssuesWidget(presenter)
        self.help_widget = ControllerHelpWidget()

        # Associate widgets with titles.
        self.widget_titles = {self.settings_widget: 'Controller Settings',
                              self.messages_widget: 'Message Center',
                              self.issues_widget: 'Issues',
                              self.help_widget: 'Help'}

        for widget in self.widget_titles.keys():
            self.stacked_widget.addWidget(widget)
            
        # Show default widget
        self.show_stacked_widget(self.settings_widget)
    