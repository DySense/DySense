#!/usr/bin/env python

import sys
from PyQt4.Qt import *
from PyQt4 import QtGui

class EndSessionDialog(QDialog):
    
    def __init__(self, presenter, controller_info, *args):
        QDialog.__init__(self, *args)
        
        self.presenter = presenter
        
        self.setWindowTitle('End Session')
        self.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
        self.setMinimumWidth(305)
        
        self.central_layout = QVBoxLayout(self)
        
        self.setup_buttons()
        
        controller_settings = controller_info['settings']
        
        self.session_notes = QTextEdit()
        self.session_notes.setMinimumHeight(30)
        self.session_notes.setLineWrapMode(QTextEdit.WidgetWidth)
        self.session_notes.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.session_notes_box = QGroupBox()
        self.session_notes_box.setTitle('Session Notes')
        self.session_notes_box.setAlignment(Qt.AlignHCenter)
        self.session_notes_box_layout = QVBoxLayout(self.session_notes_box)
        self.session_notes_box_layout.addWidget(self.session_notes)
        
        self.settings_box = QGroupBox()
        self.settings_box_layout = QGridLayout(self.settings_box)
        self.settings_box_layout.addWidget(QLabel('Controller:'), 0, 0)
        self.settings_box_layout.addWidget(QLabel(controller_info['id']), 0, 1)
        self.settings_box_layout.addWidget(QLabel('Operator:'), 1, 0)
        self.settings_box_layout.addWidget(QLabel(controller_settings['operator_name']), 1, 1)
        self.settings_box_layout.addWidget(QLabel('Platform:'), 2, 0)
        self.settings_box_layout.addWidget(QLabel(controller_settings['platform_name']), 2, 1)
        self.settings_box_layout.addWidget(QLabel('Platform ID:'), 3, 0)
        self.settings_box_layout.addWidget(QLabel(controller_settings['platform_id']), 3, 1)
        self.settings_box_layout.addWidget(QLabel('Field ID:'), 4, 0)
        self.settings_box_layout.addWidget(QLabel(controller_settings['field_id']), 4, 1)
        self.settings_box_layout.addWidget(QLabel('Surveyed:'), 5, 0)
        self.settings_box_layout.addWidget(QLabel(str(controller_settings['surveyed'])), 5, 1)
        
        self.central_layout.addWidget(self.settings_box)
        self.central_layout.addWidget(self.session_notes_box)
        self.central_layout.addLayout(self.button_layout)
        
        self.verify_button.setDefault(True)

    def setup_buttons(self):
        
        self.verify_button = QPushButton("Verify")
        self.cancel_button = QPushButton("Cancel")
        self.invalidate_button = QPushButton("Invalidate")
        self.verify_button.clicked.connect(self.verify_button_clicked)
        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.invalidate_button.clicked.connect(self.invalidate_button_clicked)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.verify_button)
        self.button_layout.addWidget(self.invalidate_button)

    def verify_button_clicked(self):

        notes = str(self.session_notes.toPlainText()).strip()
        
        self.presenter.send_controller_command('stop_session', notes, send_to_all_controllers=False)
        
        self.close()
        
    def cancel_button_clicked(self):
        
        self.close()
        
    def invalidate_button_clicked(self):
        
        question = "Are you sure you want to invalidate the current session?  This will end the session and prefix 'invalid_' to the session directory. No data will be lost."
        reply = QtGui.QMessageBox.question(self, 'Message',  question, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply != QtGui.QMessageBox.Yes:
            return

        notes = str(self.session_notes.toPlainText()).strip()

        self.presenter.send_controller_command('invalidate_session', send_to_all_controllers=False)
        self.presenter.send_controller_command('stop_session', notes, send_to_all_controllers=False)
        
        self.close()
        