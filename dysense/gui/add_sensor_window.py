#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from PyQt4.Qt import *
from PyQt4 import QtGui

from dysense.core.utility import make_unicode

class AddSensorWindow(QDialog):
    
    def __init__(self, presenter, possible_sensor_types, possible_sensor_id_types, *args):
        QDialog.__init__(self, *args)
        
        self.presenter = presenter
        self.possible_sensor_id_types = possible_sensor_id_types
        
        self.setWindowTitle('Add Sensor')
        self.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
        self.setMinimumWidth(205)
        
        self.dialog_font = QtGui.QFont()
        self.dialog_font.setPointSize(14)
        
        self.central_layout = QGridLayout(self)

        self.type_label = QLabel('Type:')
        self.name_label = QLabel('Name:')
        self.id_label = QLabel('ID:')
        self.heads_up_label = QLabel('(name cannot be changed once set)')
        
        self.type_label.setFont(self.dialog_font)
        self.name_label.setFont(self.dialog_font)
        self.id_label.setFont(self.dialog_font)

        self.sensor_type_combo_box = QComboBox()
        self.sensor_type_combo_box.setFont(self.dialog_font)
        self.sensor_type_combo_box.addItems(possible_sensor_types)
        self.sensor_type_combo_box.currentIndexChanged.connect(self.sensor_type_selected)
        
        self.sensor_name_line_edit = QLineEdit()
        self.sensor_name_line_edit.setFont(self.dialog_font)
        
        self.sensor_id_type_line_edit = QLineEdit()
        self.sensor_id_type_line_edit.setFont(self.dialog_font)
        self.sensor_id_type_line_edit.setReadOnly(True)
        self.sensor_id_type_line_edit.setMaximumWidth(60)
        self.sensor_id_type_line_edit.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.sensor_id_tag_line_edit = QLineEdit()
        self.sensor_id_tag_line_edit.setFont(self.dialog_font)
        self.sensor_id_layout = QHBoxLayout()
        self.sensor_id_layout.addWidget(self.sensor_id_type_line_edit)
        self.sensor_id_layout.addWidget(self.sensor_id_tag_line_edit)
        
        self.setup_buttons()
        
        self.central_layout.addWidget(self.type_label, 0, 0)
        self.central_layout.addWidget(self.sensor_type_combo_box, 0, 1)
        self.central_layout.addWidget(self.name_label, 1, 0)
        self.central_layout.addWidget(self.sensor_name_line_edit, 1, 1)
        self.central_layout.addWidget(self.id_label, 2, 0)
        self.central_layout.addLayout(self.sensor_id_layout, 2, 1, 1, 1)
        self.central_layout.addWidget(self.heads_up_label, 3, 1)
        self.central_layout.addLayout(self.button_layout, 4, 0, 1, 2)
        
        self.sensor_type_selected()
        self.add_button.setDefault(True)

    def setup_buttons(self):
        
        self.add_button = QPushButton("Add")
        self.cancel_button = QPushButton("Cancel")
        self.add_button.setFont(self.dialog_font)
        self.cancel_button.setFont(self.dialog_font)
        self.add_button.clicked.connect(self.add_button_clicked)
        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.add_button)

    def sensor_type_selected(self):
        self.sensor_name_line_edit.setFocus()
        try:
            sensor_id_type = self.possible_sensor_id_types[self.sensor_type_combo_box.currentIndex()]
            self.sensor_id_type_line_edit.setText(make_unicode(sensor_id_type))
        except IndexError:
            pass

    def add_button_clicked(self):

        new_sensor_info =  {'sensor_type': self.sensor_type_combo_box.currentText().strip(), 
                            'sensor_id': self.sensor_name_line_edit.text().strip(),
                            'instrument_type': self.sensor_id_type_line_edit.text().strip(),
                            'instrument_tag': self.sensor_id_tag_line_edit.text().strip()}
        
        self.presenter.add_sensor(new_sensor_info)
        
        self.close()
        
    def cancel_button_clicked(self):
        
        self.close()
        