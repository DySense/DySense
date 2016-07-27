#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from PyQt4.Qt import *
from PyQt4 import QtGui

from dysense.core.utility import make_unicode
from dysense.gui.controller_widgets.controller_settings_widget import ControllerSettingsWidget

class EndSessionDialog(QDialog):
    
    def __init__(self, controller_view, presenter, controller_info, notes, *args):
        QDialog.__init__(self, *args)
        
        self.controller_view = controller_view
        self.presenter = presenter
        
        self.setWindowTitle('End Session')
        self.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
        self.setMinimumWidth(305)
        
        self.dialog_font = QtGui.QFont()
        self.dialog_font.setPointSize(14)
        
        self.central_layout = QVBoxLayout(self)
        
        self.setup_buttons()
        
        controller_settings = controller_info['settings']
        
        self.session_notes = QTextEdit()
        self.session_notes.setMinimumHeight(50)
        self.session_notes.setLineWrapMode(QTextEdit.WidgetWidth)
        self.session_notes.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.session_notes_box = QGroupBox()
        self.session_notes.setFontPointSize(12)
        self.session_notes_box.setTitle('Session Notes')
        self.session_notes_box.setAlignment(Qt.AlignHCenter)
        self.session_notes_box.setFont(self.dialog_font)
        self.session_notes_box_layout = QVBoxLayout(self.session_notes_box)
        self.session_notes_box_layout.addWidget(self.session_notes)
        
        self.session_notes.append(notes)
        
        self.settings_box = QGroupBox()
        self.settings_box_layout = QVBoxLayout(self.settings_box)
        self.settings_box.setTitle('Controller Settings: {}'.format(controller_info['id']))
        self.settings_box.setAlignment(Qt.AlignHCenter)
        self.settings_box.setFont(self.dialog_font)
            
        self.settings_widget = ControllerSettingsWidget(presenter, controller_info, only_basic_settings=True)
        self.settings_box_layout.addWidget(self.settings_widget)
        
        self.central_layout.addWidget(self.settings_box)
        self.central_layout.addWidget(self.session_notes_box)
        self.central_layout.addLayout(self.button_layout)
        
        self.confirm_button.setDefault(True)

    def setup_buttons(self):
        
        self.confirm_button = QPushButton("Confirm")
        self.cancel_button = QPushButton("Cancel")
        self.invalidate_button = QPushButton("Invalidate")
        self.confirm_button.setFont(self.dialog_font)
        #self.cancel_button.setFont(self.dialog_font)
        #self.invalidate_button.setFont(self.dialog_font)
        self.confirm_button.clicked.connect(self.confirm_button_clicked)
        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.invalidate_button.clicked.connect(self.invalidate_button_clicked)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.confirm_button)
        self.button_layout.addWidget(self.invalidate_button)

    def confirm_button_clicked(self):

        notes = make_unicode(self.session_notes.toPlainText()).strip()
        
        self.presenter.send_controller_command('stop_session', notes, send_to_all_controllers=False)
        
        self.close()
        
    def cancel_button_clicked(self):
        
        self.controller_view.update_session_notes(make_unicode(self.session_notes.toPlainText()).strip())
        
        self.close()
        
    def invalidate_button_clicked(self):
        
        question = "Are you sure you want to invalidate the current session?  This will add an 'invalidated.txt' file to the output directory. No data will be lost."
        reply = QtGui.QMessageBox.question(self, 'Message',  question, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply != QtGui.QMessageBox.Yes:
            return

        notes = make_unicode(self.session_notes.toPlainText()).strip()

        self.presenter.send_controller_command('invalidate_session', send_to_all_controllers=False)
        self.presenter.send_controller_command('stop_session', notes, send_to_all_controllers=False)
        
        self.close()
        