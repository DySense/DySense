# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import yaml
import sys
import logging
import os

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QMetaObject, QObject, QEvent, Qt, Q_ARG
from PyQt4.QtGui import *

from dysense.gui.dysense_main_window_designer import Ui_MainWindow

class DysenseMainWindow(QMainWindow, Ui_MainWindow):
    
    def __init__(self):
        
        QMainWindow.__init__(self)

        # Set up the user interface from Designer.
        self.setupUi(self)
        
if __name__ == '__main__':
        
    app = QtGui.QApplication(sys.argv)
    main_window = DysenseMainWindow()
    
    width = main_window.frameGeometry().width()
    height = main_window.frameGeometry().height()
    print 'W {} H {}'.format(width, height)
    
    main_window.show()
    app.exec_()