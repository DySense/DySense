# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from PyQt4.Qt import *
from PyQt4 import QtGui

from dysense.core.utility import make_unicode

class ControllerHelpWidget(QWidget):

    def __init__(self, *args):
        QWidget.__init__(self, *args)

        self.setup_ui()

    def setup_ui(self):

        self.central_layout = QVBoxLayout(self)

        self.help_text_edit = QTextEdit()
        self.help_text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.help_text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.help_text_edit.setFontPointSize(10)
        self.help_text_edit.setReadOnly(True)

        self.central_layout.addWidget(self.help_text_edit)

        self.help_text_edit.setText(self.help_description())

    def help_description(self):

        return "For full instructions on getting started see the 'docs/' folder." \
               "\n\nQuick instructions:" \
               "\n - Click 'Load Config' button and select a configuration file" \
               "\n - Click 'Setup' button to setup all sensors." \
               "\n - Once all sensors are green then click 'Start' button.  If any sensors say 'Waiting for Time' then you probably need to click on 'Select Sources' to choose a time source." \
               "\n - When done collecting data click 'End' button, update the settings and click 'Confirm'"


