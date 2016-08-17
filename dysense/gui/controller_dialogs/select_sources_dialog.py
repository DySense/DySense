#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

from PyQt4.Qt import *
from PyQt4 import QtGui

from dysense.core.utility import get_from_list

class SelectSourcesDialog(QDialog):
    
    new_sources_selected = pyqtSignal(dict, list, list)
    
    def __init__(self, presenter, controller_info, sensors, *args):
        QDialog.__init__(self, *args)
        
        self.presenter = presenter
        
        self.dialog_font = QtGui.QFont()
        self.dialog_font.setPointSize(14)
        
        # Used to associate position sensor info with checkbox.
        self.checkbox_to_position_sensor = {}
        self.position_sensor_to_checkbox = {}
        
        # Used to associate height sensor info with checkbox.
        self.checkbox_to_height_sensor = {}
        self.height_sensor_to_checkbox = {}
        
        # Used to associate combo box index with sensor info.
        self.possible_time_sensors = []
        
        # Used to associated sensor info with orientation index in combo box.
        self.roll_selector_infos = []
        self.pitch_selector_infos = []
        self.yaw_selector_infos = []
        
        self.setWindowTitle('Select Sources')
        self.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
        self.setMinimumWidth(205)
        
        self.central_layout = QVBoxLayout(self)

        self.setup_time_box(controller_info, sensors)
        self.setup_orientation_box(controller_info, sensors)
        self.setup_position_box(controller_info, sensors)
        self.setup_height_source_box(controller_info, sensors)
        self.setup_buttons()
        
        self.central_layout.addWidget(self.time_group_box)
        self.central_layout.addWidget(self.position_group_box)
        self.central_layout.addWidget(self.orientation_group_box)
        self.central_layout.addWidget(self.height_group_box)
        self.central_layout.addLayout(self.button_layout)
        
    def setup_time_box(self, controller_info, sensors):
        
        self.time_group_box = QGroupBox("time")
        self.time_group_box.setTitle("Time")
        self.time_group_box.setAlignment(Qt.AlignHCenter)
        self.time_group_box.setFont(self.dialog_font)
        self.time_selector = QComboBox(self.time_group_box)
        self.time_selector.setFont(self.dialog_font)
        self.time_gb_layout = QVBoxLayout()
        self.time_gb_layout.addWidget(self.time_selector)
        self.time_group_box.setLayout(self.time_gb_layout)
        
        self.possible_time_sensors = self.find_sensors_with_tag(sensors, 'time')
        possible_time_sensors_names = [s['sensor_id'] for s in self.possible_time_sensors]

        self.time_selector.addItems(possible_time_sensors_names)
        
        try:
            current_time_id = controller_info['time_source']['sensor_id']
            current_time_sensor = [s for s in self.possible_time_sensors if s['sensor_id'] == current_time_id][0]
            active_idx = self.possible_time_sensors.index(current_time_sensor['sensor_id'])
            self.time_selector.setCurrentIndex(active_idx)
        except (ValueError, IndexError, TypeError):
            pass
        
    def setup_orientation_box(self, controller_info, sensors):
        
        self.orientation_group_box = QGroupBox("orientation")
        self.orientation_group_box.setTitle("Orientation")
        self.orientation_group_box.setAlignment(Qt.AlignHCenter)
        self.orientation_group_box.setFont(self.dialog_font)
        
        self.roll_selector = QComboBox(self.orientation_group_box)
        self.roll_label = QLabel("Roll:")
        self.roll_selector.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.roll_label.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred))
        self.roll_selector.setFont(self.dialog_font)
        self.roll_label.setFont(self.dialog_font)
        
        self.pitch_selector = QComboBox(self.orientation_group_box)
        self.pitch_label = QLabel("Pitch:")
        self.pitch_selector.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.pitch_label.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred))
        self.pitch_selector.setFont(self.dialog_font)
        self.pitch_label.setFont(self.dialog_font)
        
        self.yaw_selector = QComboBox(self.orientation_group_box)
        self.yaw_label = QLabel("Yaw:")
        self.yaw_selector.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.yaw_label.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred))
        self.yaw_selector.setFont(self.dialog_font)
        self.yaw_label.setFont(self.dialog_font)
                     
        def populate_selector(selector, angle_tag, current_orientation_source, selector_infos):
            
            selector.addItem('N/A')
            selector_infos.append({'sensor_id': 'none', 'controller_id': 'none'})
            
            selector.addItem('Derived')
            selector_infos.append({'sensor_id': 'derived', 'controller_id': 'derived'})
            
            possible_sensors = self.find_sensors_with_tag(sensors, angle_tag, tag_in_data=True)
            for sensor_info in possible_sensors:
                selector.addItem(sensor_info['sensor_id'])
                selector_infos.append(sensor_info)
        
            if current_orientation_source is not None:
                if current_orientation_source['sensor_id'].lower() == 'none':
                    selector.setCurrentIndex(selector.findText('N/A'))
                elif current_orientation_source['sensor_id'].lower() == 'derived':
                    selector.setCurrentIndex(selector.findText('Derived'))
                else:
                    for sensor_info in possible_sensors:
                        # TODO update for multiple controllers
                        if current_orientation_source['sensor_id'] == sensor_info['sensor_id']:
                            for idx, selector_info in enumerate(selector_infos):
                                if selector_info['sensor_id'] == current_orientation_source['sensor_id']:
                                    selector.setCurrentIndex(idx)
                                    break
 
        current_roll_source = get_from_list(controller_info['orientation_sources'], 0)
        current_pitch_source = get_from_list(controller_info['orientation_sources'], 1)
        current_yaw_source = get_from_list(controller_info['orientation_sources'], 2)
        
        populate_selector(self.roll_selector, 'roll', current_roll_source, self.roll_selector_infos)
        populate_selector(self.pitch_selector, 'pitch', current_pitch_source, self.pitch_selector_infos)
        populate_selector(self.yaw_selector, 'yaw', current_yaw_source, self.yaw_selector_infos)
        
        self.orientation_gb_layout = QGridLayout()
        self.orientation_gb_layout.addWidget(self.roll_label, 0, 1)
        self.orientation_gb_layout.addWidget(self.roll_selector, 0, 2)
        self.orientation_gb_layout.addWidget(self.pitch_label, 1, 1)
        self.orientation_gb_layout.addWidget(self.pitch_selector, 1, 2)
        self.orientation_gb_layout.addWidget(self.yaw_label, 2, 1)
        self.orientation_gb_layout.addWidget(self.yaw_selector, 2, 2)
        
        self.orientation_group_box.setLayout(self.orientation_gb_layout)
        
    def setup_position_box(self, controller_info, sensors):
        
        self.position_group_box = QGroupBox("position")
        self.position_group_box.setTitle("Position")
        self.position_group_box.setAlignment(Qt.AlignHCenter)
        self.position_group_box.setFont(self.dialog_font)
        
        self.position_gb_layout = QVBoxLayout()
        
        possible_position_sensors = self.find_sensors_with_tag(sensors, 'position')
        for sensor_info in possible_position_sensors:
            checkbox = QCheckBox()
            checkbox.setText(sensor_info['sensor_id'])
            checkbox.setFont(self.dialog_font)
            
            self.position_sensor_to_checkbox[sensor_info['sensor_id']] = checkbox
            self.checkbox_to_position_sensor[checkbox] = sensor_info
            
            # TODO update for multiple controllers
            for current_position_source in controller_info['position_sources']:
                if current_position_source['sensor_id'] == sensor_info['sensor_id']:
                    checkbox.setChecked(True)
            
            self.position_gb_layout.addWidget(checkbox)
        
        self.position_group_box.setLayout(self.position_gb_layout)
        
    def setup_height_source_box(self, controller_info, sensors):
        
        self.height_group_box = QGroupBox("height")
        self.height_group_box.setTitle("Height Above Ground")
        self.height_group_box.setAlignment(Qt.AlignHCenter)
        self.height_group_box.setFont(self.dialog_font)
        
        self.height_gb_layout = QVBoxLayout()
        
        possible_height_sensors = self.find_sensors_with_tag(sensors, 'height', tag_in_data=True)
        for sensor_info in possible_height_sensors:
            checkbox = QCheckBox()
            checkbox.setText(sensor_info['sensor_id'])
            checkbox.setFont(self.dialog_font)
            
            self.height_sensor_to_checkbox[sensor_info['sensor_id']] = checkbox
            self.checkbox_to_height_sensor[checkbox] = sensor_info
            
            # TODO update for multiple controllers
            for current_height_source in controller_info.get('height_sources',[]):
                if current_height_source['sensor_id'] == sensor_info['sensor_id']:
                    checkbox.setChecked(True)
            
            self.height_gb_layout.addWidget(checkbox)
        
        self.height_group_box.setLayout(self.height_gb_layout)

    def setup_buttons(self):
        
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.setFont(self.dialog_font)
        self.cancel_button.setFont(self.dialog_font)
        self.ok_button.clicked.connect(self.ok_button_clicked)
        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.ok_button)
        
        self.ok_button.setDefault(True)

    def find_sensors_with_tag(self, sensors, tag, tag_in_data=False):
        
        sensor_info_with_tag = []
        for sensor_info in sensors.values():
            metadata = sensor_info['metadata']
            
            if tag_in_data:
                # Look through tags on specified pieces of output data.
                for sensor_data in metadata['data']:
                    if tag in [t.lower() for t in sensor_data.get('tags', [])]:
                        sensor_info_with_tag.append(sensor_info)
            else: 
                # Look through tags associated with general sensor metadata.
                if tag in [t.lower() for t in metadata.get('tags', [])]:
                    sensor_info_with_tag.append(sensor_info)
        
        return sensor_info_with_tag
    
    def ok_button_clicked(self):
        
        try:
            time_source_info = self.possible_time_sensors[self.time_selector.currentIndex()]
        except IndexError:
            time_source_info = None
        
        position_sources = []
        for checkbox, sensor_info in self.checkbox_to_position_sensor.iteritems():
            if checkbox.isChecked():
                position_sources.append(sensor_info)
        
        roll_source = self.roll_selector_infos[self.roll_selector.currentIndex()]
        pitch_source = self.pitch_selector_infos[self.pitch_selector.currentIndex()]
        yaw_source = self.yaw_selector_infos[self.yaw_selector.currentIndex()]
        
        orientation_sources = [roll_source, pitch_source, yaw_source]
        
        height_sources = []
        for checkbox, sensor_info in self.checkbox_to_height_sensor.iteritems():
            if checkbox.isChecked():
                height_sources.append(sensor_info)
        
        self.presenter.change_controller_info('time_source', time_source_info)
        self.presenter.change_controller_info('position_sources', position_sources)
        self.presenter.change_controller_info('orientation_sources', orientation_sources)
        self.presenter.change_controller_info('height_sources', height_sources)
        
        self.close()
        
    def cancel_button_clicked(self):
        
        self.close()
        