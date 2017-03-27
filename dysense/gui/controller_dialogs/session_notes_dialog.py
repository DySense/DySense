#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from PyQt4.Qt import *
from PyQt4 import QtGui

from dysense.core.utility import make_unicode

class SessionNotesDialog(QDialog):

    def __init__(self, controller_view, notes, *args):
        QDialog.__init__(self, *args)

        self.controller_view = controller_view

        self.setup_ui(notes)

    def setup_ui(self, notes):

        self.setWindowTitle('Notes')
        self.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
        self.setMinimumWidth(500)
        #self.setMaximumWidth(800)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.dialog_font = QtGui.QFont()
        self.dialog_font.setPointSize(14)

        self.central_layout = QVBoxLayout(self)

        self.session_notes = QTextEdit()
        self.session_notes.setMinimumHeight(200)
        self.session_notes.setLineWrapMode(QTextEdit.WidgetWidth)
        self.session_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.session_notes_box = QGroupBox()
        self.session_notes.setFontPointSize(12)
        self.session_notes_box.setTitle('Session Notes')
        self.session_notes_box.setAlignment(Qt.AlignHCenter)
        self.session_notes_box.setFont(self.dialog_font)
        self.session_notes_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.session_notes_box_layout = QVBoxLayout(self.session_notes_box)
        self.session_notes_box_layout.addWidget(self.session_notes)

        # Load the notes that have already been saved
        self.session_notes.append(notes)

        self.confirm_button = QPushButton("OK")
        self.confirm_button.setFont(self.dialog_font)
        self.confirm_button.clicked.connect(self.confirm_button_clicked)

        self.central_layout.addWidget(self.session_notes_box)
        self.central_layout.addWidget(self.confirm_button)

        self.confirm_button.setDefault(True)

    def confirm_button_clicked(self):

        # Handle saving notes in closeEvent so it will save even if user hits red 'X' to close dialog.
        self.close()

    def closeEvent(self, *args, **kwargs):

        notes = make_unicode(self.session_notes.toPlainText()).strip()

        self.controller_view.update_session_notes(notes)

        return QDialog.closeEvent(self, *args, **kwargs)


