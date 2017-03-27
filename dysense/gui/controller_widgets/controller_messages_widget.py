# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from PyQt4.Qt import *
from PyQt4 import QtGui

from dysense.core.utility import make_unicode

class ControllerMessagesWidget(QWidget):

    def __init__(self, *args):
        QWidget.__init__(self, *args)

        self.setup_ui()

    def setup_ui(self):

        self.button_font = QtGui.QFont()
        self.button_font.setPointSize(12)

        self.central_layout = QVBoxLayout(self)

        self.messages_text_edit = QTextEdit()
        self.messages_text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.messages_text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.messages_text_edit.setFontPointSize(10)
        self.messages_text_edit.setReadOnly(True)

        self.clear_button = QPushButton("Clear Messages")
        self.clear_button.setFont(self.button_font)
        self.clear_button.clicked.connect(self.clear_button_clicked)
        self.clear_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.central_layout.addWidget(self.messages_text_edit)
        self.central_layout.addWidget(self.clear_button)

    def clear_button_clicked(self):

        self.messages_text_edit.clear()

    def append_message(self, new_message):

        self.messages_text_edit.append(new_message)