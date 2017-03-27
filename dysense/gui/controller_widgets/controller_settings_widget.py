# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import copy

from PyQt4.Qt import *
from PyQt4 import QtGui, QtCore

from dysense.core.utility import make_unicode, pretty, format_setting

class ControllerSettingsWidget(QWidget):

    def __init__(self, presenter, controller_info, only_basic_settings=False, *args):
        QWidget.__init__(self, *args)

        self.presenter = presenter
        self.controller_id = controller_info['id']
        self.controller_settings = copy.deepcopy(controller_info['settings'])
        self.extra_settings = copy.deepcopy(controller_info['extra_settings'])
        self.only_basic_settings = only_basic_settings

        self.setup_ui()

    def setup_ui(self):

        self.widget_font = QtGui.QFont()
        self.widget_font.setPointSize(13)

        # Widget -> Scroll Area -> Frame (Grid Layout)

        self.scroll_area = QtGui.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        #self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.scroll_area)

        if not self.only_basic_settings:
            self.setup_buttons()

        self.setup_settings_frame(self.controller_settings, self.extra_settings)

    def setup_settings_frame(self, settings, extra_settings):

        self.controller_settings = settings
        self.extra_settings = extra_settings

        # Add Controller ID to list of settings so it gets generated on the widget.
        self.controller_settings['id'] = self.controller_id

        # Populated from controller settings to relate widgets and settings.
        self.setting_name_to_object = {}
        self.object_to_setting_name = {}

        self.settings_frame = QtGui.QFrame()
        self.settings_frame_layout = QGridLayout()
        self.settings_frame.setLayout(self.settings_frame_layout)

        self.scroll_area.setWidget(self.settings_frame)

        # Override certain settings so they show something different for the text label.
        # (e.g. replace 'id' with 'controller id' since it's more descriptive for the user to see)
        settings_name_override = {'id': 'Controller ID',
                                  'base_out_directory': 'Output Folder'}

        # Define what order settings will show up in widget.
        settings_order = ['id', 'base_out_directory', 'operator_name', 'platform_type', 'platform_tag', 'surveyed']

        setting_name_to_tooltip = {'id': 'Name of this computer. Should be unique.',
                                   'base_out_directory': 'Base folder where new session folders will be saved.',
                                   'operator_name': 'First and last name of person in charge of session.',
                                   'platform_type': 'Name associated with this type of platform.',
                                   'platform_tag': 'Unique ID of platform (e.g. serial number)',
                                   'surveyed': 'If using RTK then set to False if base station location is not surveyed. If not using RTK then always set to True',
                                   }

        # Convert settings to an ordered list so they show up in a consistent order.
        ordered_controller_settings = []
        for ordered_name in settings_order:
            try:
                setting_value = self.controller_settings[ordered_name]
            except KeyError:
                continue # setting not available.

            ordered_controller_settings.append((ordered_name, setting_value))

        # Add on extra settings in alphabetical order.
        for extra_setting_name, extra_setting_value in sorted(self.extra_settings.items()):
            ordered_controller_settings.append((extra_setting_name, extra_setting_value))

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
            text_label.setFont(self.widget_font)
            value_line_edit.setFont(self.widget_font)

            tooltip = setting_name_to_tooltip.get(setting_name,'')
            text_label.setToolTip(tooltip)
            value_line_edit.setToolTip(tooltip)

            value_line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            self.settings_frame_layout.addWidget(text_label, i, 0)

            if setting_name == 'base_out_directory':
                # Need to add special browse button next to line edit.
                self.settings_frame_layout.addLayout(self.browse_layout(value_line_edit), i, 1)
            else:
                self.settings_frame_layout.addWidget(value_line_edit, i, 1)

            self.object_to_setting_name[value_line_edit] = setting_name
            self.setting_name_to_object[setting_name] = value_line_edit

            # Connect signal so we know when value changes
            value_line_edit.editingFinished.connect(self.value_changed_by_user)

    def setup_buttons(self):

        self.add_setting_button = QPushButton()
        self.add_setting_button.setText("   Add New Setting   ")
        self.add_setting_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        self.remove_setting_button = QPushButton()
        self.remove_setting_button.setText("   Remove Setting   ")
        self.remove_setting_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.add_setting_button)
        self.button_layout.addWidget(self.remove_setting_button)

        self.main_layout.addLayout(self.button_layout)

        self.add_setting_button.clicked.connect(self.add_setting_button_clicked)
        self.remove_setting_button.clicked.connect(self.remove_setting_button_clicked)

    def browse_layout(self, line_edit):

        browse_button = QPushButton('Select')
        browse_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        browse_button.clicked.connect(self.browse_button_clicked)

        layout = QHBoxLayout()
        layout.addWidget(line_edit)
        layout.addWidget(browse_button)

        return layout

    def browse_button_clicked(self):

        output_directory = QFileDialog.getExistingDirectory(self, "Select Directory", os.path.expanduser('~'))

        if not output_directory:
            return # User didn't select a directory.

        line_edit = self.setting_name_to_object['base_out_directory']

        line_edit.setText(output_directory)
        line_edit.setModified(True)
        line_edit.editingFinished.emit()

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

    def add_setting_button_clicked(self):

        self.add_setting_dialog = AddNewSettingDialog(self.presenter)
        self.add_setting_dialog.setModal(True)
        self.add_setting_dialog.show()

    def remove_setting_button_clicked(self):

        self.remove_setting_dialog = RemoveNewSettingDialog(self.presenter, self.extra_settings)
        self.remove_setting_dialog.setModal(True)
        self.remove_setting_dialog.show()

class AddNewSettingDialog(QDialog):

    def __init__(self, presenter, *args):
        QDialog.__init__(self, *args)

        self.presenter = presenter

        self.setup_ui()

    def setup_ui(self):

        self.setWindowTitle('Add New Setting')
        self.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
        self.setMinimumWidth(205)

        self.dialog_font = QtGui.QFont()
        self.dialog_font.setPointSize(14)

        self.central_layout = QGridLayout(self)

        self.name_label = QLabel('Setting Name:')
        self.type_label = QLabel('Type')
        self.name_label.setFont(self.dialog_font)
        self.type_label.setFont(self.dialog_font)

        self.name_line_edit = QLineEdit()
        self.name_line_edit.setFont(self.dialog_font)

        self.possible_setting_types = ['string', 'integer', 'float', 'boolean']
        self.possible_setting_descriptions = ['Text', 'Integer', 'Number with Decimals', 'True/False']
        self.possible_setting_defaults = ['', 0, 0.0, True]

        self.setting_type_combo_box = QComboBox()
        self.setting_type_combo_box.setFont(self.dialog_font)
        self.setting_type_combo_box.addItems(self.possible_setting_descriptions)
        self.setting_type_combo_box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setting_type_combo_box.setMaxVisibleItems(10)

        self.add_button = QPushButton("Add")
        self.cancel_button = QPushButton("Cancel")
        self.add_button.setFont(self.dialog_font)
        self.cancel_button.setFont(self.dialog_font)
        self.add_button.clicked.connect(self.add_button_clicked)
        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.add_button)

        self.central_layout.addWidget(self.name_label, 1, 1)
        self.central_layout.addWidget(self.name_line_edit, 1, 2)
        self.central_layout.addWidget(self.type_label, 2, 1)
        self.central_layout.addWidget(self.setting_type_combo_box, 2, 2)
        self.central_layout.addLayout(self.button_layout, 3, 1, 1, 2)

        self.add_button.setDefault(True)

    def add_button_clicked(self):

        selected_type_index = self.setting_type_combo_box.currentIndex()
        selected_type = self.possible_setting_types[selected_type_index]
        selected_default_value = self.possible_setting_defaults[selected_type_index]

        setting_name = self.name_line_edit.text()

        args = (setting_name, selected_type, selected_default_value)

        self.presenter.send_controller_command('add_extra_setting', args, send_to_all_controllers=False)

        self.close()

    def cancel_button_clicked(self):

        self.close()

class RemoveNewSettingDialog(QDialog):

    def __init__(self, presenter, extra_setting_names, *args):
        QDialog.__init__(self, *args)

        self.presenter = presenter
        self.extra_setting_names = extra_setting_names

        self.setup_ui()

    def setup_ui(self):

        self.setWindowTitle('Remove Setting')
        self.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
        self.setMinimumWidth(205)

        self.dialog_font = QtGui.QFont()
        self.dialog_font.setPointSize(14)

        self.central_layout = QGridLayout(self)

        self.setting_combo_box = QComboBox()
        self.setting_combo_box.setFont(self.dialog_font)
        self.setting_combo_box.addItems(sorted(self.extra_setting_names.keys()))
        self.setting_combo_box.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setting_combo_box.setMaxVisibleItems(15)

        self.remove_button = QPushButton("Remove")
        self.cancel_button = QPushButton("Cancel")
        self.remove_button.setFont(self.dialog_font)
        self.cancel_button.setFont(self.dialog_font)
        self.remove_button.clicked.connect(self.remove_button_clicked)
        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.remove_button)

        self.central_layout.addWidget(self.setting_combo_box, 1, 1)
        self.central_layout.addLayout(self.button_layout, 2, 1, 1, 1)

        self.remove_button.setDefault(True)

    def remove_button_clicked(self):

        selected_setting_name = self.setting_combo_box.currentText()

        self.presenter.send_controller_command('remove_extra_setting', selected_setting_name, send_to_all_controllers=False)

        self.close()

    def cancel_button_clicked(self):

        self.close()