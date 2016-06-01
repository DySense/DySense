#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
import os
import math
from PyQt4.Qt import *
from PyQt4 import QtGui

class NewIssuePopupWindow(QDialog):
    
    def __init__(self, *args):
        QDialog.__init__(self, *args)
        
        self.setWindowFlags(Qt.Popup)

        self.setMinimumWidth(305 * 1.5)
        self.setMinimumHeight(155 * 1.5)
        
        self.popup_closed = False
        
        self.main_label = QLabel('NEW ISSUE')
        font = QtGui.QFont()
        font.setPointSize(55)
        font.setBold(True)
        self.main_label.setFont(font)
        
        self.central_layout = QVBoxLayout(self)
        self.central_layout.addWidget(self.main_label)

        self.setMouseTracking(True)
        self.starting_mouse_x = None
        self.starting_mouse_y = None
        
        #self.flash_timer = QTimer()
        #self.flash_timer.timeout.connect(self.flash_timer_elapsed)
        #self.flash_timer.start(0.2 * 1000)
        self.flash_timer_elapsed()

    def mouseMoveEvent(self, mouse_event):
        x = mouse_event.pos().x()
        y = mouse_event.pos().y()
        if self.starting_mouse_x is None:
            self.starting_mouse_x = x 
            self.starting_mouse_y = y
        else:
            diffx = self.starting_mouse_x - x
            diffy = self.starting_mouse_y - y 
            movement = math.sqrt(diffx*diffx + diffy*diffy)
            if movement > 10:
                self.close_down()

    def keyPressEvent(self, *args, **kwargs):
        self.close_down()
        
    def mousePressEvent(self, *args, **kwargs):
        self.close_down()
        
    def close_down(self):
        self.popup_closed = True
        #self.flash_timer.stop()
        self.setMouseTracking(False)
        self.close()
        
    def flash_timer_elapsed(self):
        
        if self.popup_closed:
            return
        
        if self.isVisible():
            self.setVisible(False)
            #self.activateWindow()
            QTimer.singleShot(0.05 * 1000, self.flash_timer_elapsed)
        else:
            self.setVisible(True)
            self.activateWindow()
            QTimer.singleShot(1 * 1000, self.flash_timer_elapsed)
            
            sys.stdout.write('\a')  # Cross platform alert noise