#!/usr/bin/env python

import sys
from PyQt4.Qt import *
from PyQt4 import QtGui

class AddSensorWindow(QDialog):
    
    def __init__(self, presenter, possible_sensor_types, *args):
        QDialog.__init__(self, *args)
        
        self.presenter = presenter
        
        self.setWindowTitle('Add Sensor')
        self.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
        self.setMinimumWidth(205)
        
        self.central_layout = QGridLayout(self)

        self.type_label = QLabel('Type:')
        self.name_label = QLabel('Name:')
        self.heads_up_label = QLabel('(name cannot be changed once set)')

        self.sensor_type_combo_box = QComboBox()
        self.sensor_type_combo_box.addItems(possible_sensor_types)
        self.sensor_type_combo_box.currentIndexChanged.connect(self.sensor_type_selected)
        
        self.sensor_name_line_edit = QLineEdit()
        
        self.setup_buttons()
        
        self.central_layout.addWidget(self.type_label, 0, 0)
        self.central_layout.addWidget(self.sensor_type_combo_box, 0, 1)
        self.central_layout.addWidget(self.name_label, 1, 0)
        self.central_layout.addWidget(self.sensor_name_line_edit, 1, 1)
        self.central_layout.addWidget(self.heads_up_label, 2, 1)
        self.central_layout.addLayout(self.button_layout, 3, 0, 1, 2)
        
        self.sensor_name_line_edit.setFocus()
        self.add_button.setDefault(True)

    def setup_buttons(self):
        
        self.add_button = QPushButton("Add")
        self.cancel_button = QPushButton("Cancel")
        self.add_button.clicked.connect(self.add_button_clicked)
        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.add_button)

    def sensor_type_selected(self):
        self.sensor_name_line_edit.setFocus()

    def add_button_clicked(self):

        new_sensor_info =  {'sensor_type': str(self.sensor_type_combo_box.currentText()).strip(), 
                            'sensor_name': str(self.sensor_name_line_edit.text()).strip()}
        
        self.presenter.add_sensor(new_sensor_info)
        
        self.close()
        
    def cancel_button_clicked(self):
        
        self.close()
        