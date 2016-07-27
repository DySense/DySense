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
    
    def __init__(self, presenter, main_window, *args):
        QWidget.__init__(self, *args)
        
        self.presenter = presenter
        self.main_window = main_window

        self.setup_ui()
        
    def setup_ui(self):
        
        self.widget_font = QtGui.QFont()
        self.widget_font.setPointSize(14)
        
        self.central_layout = QGridLayout(self)
        
        self.load_button_icons()
        
        ButtonInfo = collections.namedtuple('ButtonInfo', 'text, row, column, callback, icon_name')
        
        self.button_info = [ButtonInfo('Open Session Output', 0, 0, self.open_output_clicked, 'view_output_icon'),
                            ButtonInfo('Map', 0, 1, self.view_map_clicked, None),
                            ButtonInfo('View All Sensor Data', 0, 2, self.view_sensor_data_clicked, None)
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
            menu_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            menu_button.setMaximumSize(500, 500)
            
            self.menu_buttons.append(menu_button)
        
            self.central_layout.addWidget(menu_button, info.row, info.column)

    def load_button_icons(self):
        
        resources_directory = '../resources/command_icons'
        icon_extension = '.png'
        self.icon_names =  ['view_output_icon']
        
        self.icon_name_to_icon = {}
        
        for icon_name in self.icon_names:
            icon_file_name = icon_name + icon_extension
            icon_path = os.path.join(resources_directory, icon_file_name)
            icon = QtGui.QIcon(icon_path)
            self.icon_name_to_icon[icon_name] = icon
        
    def view_map_clicked(self):
        
        print 'show map'
        
    def view_sensor_data_clicked(self):
        
        self.main_window.show_sensor_data_table()
        
    def open_output_clicked(self):
        
        session_path = self.presenter.local_controller['session_path']
        if session_path is None or session_path.strip().lower() in ['none', '']:
            self.main_window.show_user_message('Need to start a session first.', logging.INFO)
            return
        open_directory_in_viewer(session_path)
        
    def icon_size_for_button_size(self, min_button_dimension, font):
            
        icon_pad = min_button_dimension * .1
        text_height = QFontMetrics(font).height()
        
        icon_width = min_button_dimension - icon_pad
        icon_height = min_button_dimension - text_height

        return icon_width, icon_height
    
    def resizeEvent(self, event_info):
        
        for menu_button in self.menu_buttons:
            
            min_button_dimension = min(menu_button.width(), menu_button.height())
            
            width, height = self.icon_size_for_button_size(min_button_dimension, menu_button.font())
            
            min_icon_dimension = min(width, height)
            
            menu_button.setIconSize(QSize(min_button_dimension, min_icon_dimension))
    
    def resize_menu_icons(self):
        
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
        
  