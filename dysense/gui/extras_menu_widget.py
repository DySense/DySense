# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from PyQt4.Qt import *
from PyQt4 import QtGui
from PyQt4 import QtCore

import collections
import os
import logging

from dysense.core.utility import make_unicode, open_directory_in_viewer

class ExtrasMenuWidget(QWidget):
    
    def __init__(self, presenter, main_window, sensor_data_table, map_widget, *args):
        QWidget.__init__(self, *args)
        
        self.presenter = presenter
        self.main_window = main_window
        self.sensor_data_table = sensor_data_table
        self.map_widget = map_widget

        self.setup_ui()
        
    def setup_ui(self):
        
        self.widget_font = QtGui.QFont()
        self.widget_font.setPointSize(14)
        
        self.central_layout = QVBoxLayout(self)
        
        self.icon_layout = QHBoxLayout()
        
        self.load_button_icons()
        
        ButtonInfo = collections.namedtuple('ButtonInfo', 'text, row, column, callback, icon_name')
        
        self.button_info = [ButtonInfo('Session Output', 0, 0, self.open_output_clicked, 'open_output_icon'),
                            ButtonInfo('Map', 0, 1, self.view_map_clicked, 'map_icon'),
                            ButtonInfo('Sensor Data', 0, 2, self.view_sensor_data_clicked, 'view_sensor_data_icon')
                            ]
        
        self.menu_buttons = []
        
        for info in self.button_info:
            menu_button = QToolButton()
            menu_button.setText(info.text)
            menu_button.setFont(self.widget_font)
            if info.icon_name is not None:
                icon = self.icon_name_to_icon[info.icon_name]
                menu_button.setIcon(icon)
                menu_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            menu_button.clicked.connect(info.callback)
            menu_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
            menu_button.setAutoRaise(True)
            #menu_button.setMaximumSize(500, 500)
            
            self.menu_buttons.append(menu_button)
        
            self.icon_layout.addWidget(menu_button)
            # KLM - this is for grid layout - switch to horizontal layout
            #self.icon_layout.addWidget(menu_button, info.row, info.column)
        
        ## SETUP STACKED WIDGET
        
        self.stacked_widget = QtGui.QStackedWidget()
        self.stacked_widget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding))
        
        self.stacked_widget.addWidget(self.sensor_data_table)
        self.stacked_widget.addWidget(self.map_widget)
        
        ## ADD WIDGETS / LAYOUTS TO CENTRAL WIDGET
        
        self.central_layout.addLayout(self.icon_layout)
        self.central_layout.addWidget(self.stacked_widget)
        
        # Show default widget
        self.show_stacked_widget(self.map_widget)

    def show_stacked_widget(self, widget_ref):
        
        self.stacked_widget.setCurrentWidget(widget_ref)

    def load_button_icons(self):
        
        resources_directory = '../resources/command_icons'
        icon_extension = '.png'
        self.icon_names =  ['view_sensor_data_icon',
                            'map_icon',
                            'open_output_icon']
        
        self.icon_name_to_icon = {}
        
        for icon_name in self.icon_names:
            icon_file_name = icon_name + icon_extension
            icon_path = os.path.join(resources_directory, icon_file_name)
            icon = QtGui.QIcon(icon_path)
            self.icon_name_to_icon[icon_name] = icon
        
    def view_map_clicked(self):
        
        self.show_stacked_widget(self.map_widget)
        
    def view_sensor_data_clicked(self):
        
        self.show_stacked_widget(self.sensor_data_table)
        
    def open_output_clicked(self):
        
        session_path = self.presenter.local_controller['session_path']
        if session_path is None or session_path.strip().lower() in ['none', '']:
            self.main_window.show_user_message('Need to start a session first.', logging.INFO)
            return
        open_directory_in_viewer(session_path)
        
    def resizeEvent(self, event_info):
        
        self.resize_icons()
    
    def resize_icons(self):
        
        new_width = self.width()
        new_height = self.height()
        
        max_height = new_height * .18
        max_width = (new_width) / len(self.button_info)
        
        min_button_dimension = min(max_height, max_width)
        
        new_icon_width, new_icon_height = self.icon_size_for_button_size(min_button_dimension, self.menu_buttons[0].font())
        
        # Keep a square
        new_icon_dimension = min(new_icon_height, new_icon_width)
        
        for menu_button in self.menu_buttons:

            menu_button.setIconSize(QSize(new_icon_dimension, new_icon_dimension))
        
    def icon_size_for_button_size(self, min_button_dimension, font):
            
        icon_pad = min_button_dimension * .1
        text_height = QFontMetrics(font).height()
        
        icon_width = min_button_dimension - icon_pad
        icon_height = min_button_dimension - text_height

        return icon_width, icon_height