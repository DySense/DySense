# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import math
import sys
import time
from collections import namedtuple

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class MapView(QtGui.QGraphicsView):

    def __init__(self, parent):
        '''Constructor'''
        QtGui.QGraphicsView.__init__(self, parent)

        self.parent = parent

        self._pixels_per_meter = 0

        # Disable scroll bars since all points should already fit on screen.
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.setScene(QtGui.QGraphicsScene(self))
        self.update_after_resize()

        # Amount of space in pixels to leave on each edge.
        self._edge_pad = 20

        # The most recent point drawn by drawPoint() that was marked as temporary
        self.last_temporary_point = None

        self.reset_map()

    @property
    def drawable_width(self):
        '''Width of scene in pixels that's used for drawing points.'''
        return self.sceneRect().size().width() - (2 * self._edge_pad)

    @property
    def drawable_height(self):
        '''Height of scene in pixels that's used for drawing points.'''
        return self.sceneRect().size().height() - self._edge_pad - 70

    @property
    def center_x(self):
        '''Return X coordinate in pixels of the center of scene'''
        return self.sceneRect().size().width() / 2

    @property
    def center_y(self):
        '''Return X coordinate in pixels of the center of scene'''
        return self.sceneRect().size().height() / 2

    def update_pixels_per_meter(self, new_value):
        # Define how many view pixels in a meter. Will update scale bars or any other part of the map that depends on this value.
        self._pixels_per_meter = new_value
        self._update_scale_bar_text()

    def reset_map(self):
        '''Restore map to it's default state when the class was first created.'''
        self.scene().clear()
        self._draw_scale_bar()
        self.last_temporary_point = None

    def update_after_resize(self):
        '''Should be called by parent whenever this view changes size.'''
        self._resize_scene_to_view()

    def draw_point(self, x_pix, y_pix, temporary=False, color=Qt.green, radius=7, zvalue=0):
        '''
        Draw new circle at specified (x,y) location where origin is in top left.
         If x or y is NaN then will draw in the center.
        '''
        if math.isnan(x_pix):
            x_pix = self.center_x
        if math.isnan(y_pix):
            y_pix = self.center_y

        x_pix += self._edge_pad
        y_pix += self._edge_pad

        new_point = self.scene().addEllipse(x_pix, y_pix, radius, radius)
        new_point.setBrush(color)
        new_point.setZValue(zvalue)

        if self.last_temporary_point is not None:
            self.scene().removeItem(self.last_temporary_point)
            self.last_temporary_point = None

        if temporary:
            self.last_temporary_point = new_point

    def _draw_scale_bar(self):

        self.scale_length = 100 # pixels
        vert_line_length = 15 # pixels
        y_pos_scale = self.height() - 2 * vert_line_length
        x_pos1_scale = self.center_x - (self.scale_length / 2)
        x_pos2_scale = self.center_x + (self.scale_length / 2)

        pen = QPen(Qt.black, 3)

        # Set horizontal lines of scale bar
        self.line1 = QLineF(x_pos1_scale, y_pos_scale, x_pos2_scale, y_pos_scale)
        line_item1 = QGraphicsLineItem(self.line1, scene=self.scene())
        line_item1.setPen(pen)

        # Set vertical lines of scale bar
        self.line2 = QLineF(x_pos1_scale, y_pos_scale, x_pos1_scale, y_pos_scale-vert_line_length)
        self.line3 = QLineF(x_pos2_scale, y_pos_scale-vert_line_length, x_pos2_scale, y_pos_scale)
        self.line_item2 = QGraphicsLineItem(self.line2, scene=self.scene())
        self.line_item3 = QGraphicsLineItem(self.line3, scene=self.scene())
        self.line_item2.setPen(pen)
        self.line_item3.setPen(pen)

        x_pos_text = self.center_x - (self.scale_length / 2) + 20
        y_pos_text = y_pos_scale

        self.scale_text = QGraphicsTextItem(scene = self.scene())
        self.scale_text.adjustSize()
        self.scale_text.setPos(x_pos_text, y_pos_text)

        self._update_scale_bar_text()

    def _update_scale_bar_text(self):
        '''Update length of scale bar based on the current pixels_per_meter ratio.'''

        if math.isnan(self._pixels_per_meter) or self._pixels_per_meter == 0:
            scale_value = 0.01
        else:
            scale_value = (self.scale_length / self._pixels_per_meter)

        self.scale_text.setPlainText('%.2f Meters' % scale_value)

    def _resize_scene_to_view(self):
        '''
        Set the scene size to the full area of the view.
        This makes accessing sceneRect() much faster because it's not
        calculating it each time based on what's in the scene.
        '''
        self.setSceneRect(QtCore.QRectF(self.viewport().rect()))
