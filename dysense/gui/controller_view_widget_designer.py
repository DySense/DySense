# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'controller_view_widget_designer.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_controller_view(object):
    def setupUi(self, controller_view):
        controller_view.setObjectName(_fromUtf8("controller_view"))
        controller_view.resize(630, 480)
        self.verticalLayout = QtGui.QVBoxLayout(controller_view)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.controller_title = QtGui.QLabel(controller_view)
        font = QtGui.QFont()
        font.setPointSize(16)
        font.setBold(True)
        font.setUnderline(True)
        font.setWeight(75)
        self.controller_title.setFont(font)
        self.controller_title.setAlignment(QtCore.Qt.AlignCenter)
        self.controller_title.setObjectName(_fromUtf8("controller_title"))
        self.verticalLayout.addWidget(self.controller_title)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.session_status_label_fixed = QtGui.QLabel(controller_view)
        font = QtGui.QFont()
        font.setPointSize(16)
        self.session_status_label_fixed.setFont(font)
        self.session_status_label_fixed.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.session_status_label_fixed.setObjectName(_fromUtf8("session_status_label_fixed"))
        self.horizontalLayout.addWidget(self.session_status_label_fixed)
        self.session_status_label = QtGui.QLabel(controller_view)
        font = QtGui.QFont()
        font.setPointSize(16)
        self.session_status_label.setFont(font)
        self.session_status_label.setObjectName(_fromUtf8("session_status_label"))
        self.horizontalLayout.addWidget(self.session_status_label)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        spacerItem2 = QtGui.QSpacerItem(5, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem2)
        self.setup_sensors_button = QtGui.QToolButton(controller_view)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.setup_sensors_button.sizePolicy().hasHeightForWidth())
        self.setup_sensors_button.setSizePolicy(sizePolicy)
        self.setup_sensors_button.setMinimumSize(QtCore.QSize(90, 90))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.setup_sensors_button.setFont(font)
        self.setup_sensors_button.setIconSize(QtCore.QSize(80, 80))
        self.setup_sensors_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.setup_sensors_button.setAutoRaise(True)
        self.setup_sensors_button.setObjectName(_fromUtf8("setup_sensors_button"))
        self.horizontalLayout_2.addWidget(self.setup_sensors_button)
        spacerItem3 = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem3)
        self.start_button = QtGui.QToolButton(controller_view)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.start_button.sizePolicy().hasHeightForWidth())
        self.start_button.setSizePolicy(sizePolicy)
        self.start_button.setMinimumSize(QtCore.QSize(90, 90))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.start_button.setFont(font)
        self.start_button.setIconSize(QtCore.QSize(80, 80))
        self.start_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.start_button.setAutoRaise(True)
        self.start_button.setObjectName(_fromUtf8("start_button"))
        self.horizontalLayout_2.addWidget(self.start_button)
        spacerItem4 = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem4)
        self.pause_button = QtGui.QToolButton(controller_view)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pause_button.sizePolicy().hasHeightForWidth())
        self.pause_button.setSizePolicy(sizePolicy)
        self.pause_button.setMinimumSize(QtCore.QSize(90, 90))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pause_button.setFont(font)
        self.pause_button.setIconSize(QtCore.QSize(80, 80))
        self.pause_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.pause_button.setAutoRaise(True)
        self.pause_button.setObjectName(_fromUtf8("pause_button"))
        self.horizontalLayout_2.addWidget(self.pause_button)
        spacerItem5 = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem5)
        self.notes_button = QtGui.QToolButton(controller_view)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.notes_button.sizePolicy().hasHeightForWidth())
        self.notes_button.setSizePolicy(sizePolicy)
        self.notes_button.setMinimumSize(QtCore.QSize(90, 90))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.notes_button.setFont(font)
        self.notes_button.setIconSize(QtCore.QSize(80, 80))
        self.notes_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.notes_button.setAutoRaise(True)
        self.notes_button.setObjectName(_fromUtf8("notes_button"))
        self.horizontalLayout_2.addWidget(self.notes_button)
        spacerItem6 = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem6)
        self.end_button = QtGui.QToolButton(controller_view)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.end_button.sizePolicy().hasHeightForWidth())
        self.end_button.setSizePolicy(sizePolicy)
        self.end_button.setMinimumSize(QtCore.QSize(90, 90))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.end_button.setFont(font)
        self.end_button.setIconSize(QtCore.QSize(80, 80))
        self.end_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.end_button.setAutoRaise(True)
        self.end_button.setObjectName(_fromUtf8("end_button"))
        self.horizontalLayout_2.addWidget(self.end_button)
        spacerItem7 = QtGui.QSpacerItem(5, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem7)
        self.horizontalLayout_2.setStretch(1, 1)
        self.horizontalLayout_2.setStretch(3, 1)
        self.horizontalLayout_2.setStretch(5, 1)
        self.horizontalLayout_2.setStretch(7, 1)
        self.horizontalLayout_2.setStretch(9, 1)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.separator_line = QtGui.QFrame(controller_view)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.separator_line.sizePolicy().hasHeightForWidth())
        self.separator_line.setSizePolicy(sizePolicy)
        self.separator_line.setFrameShape(QtGui.QFrame.HLine)
        self.separator_line.setFrameShadow(QtGui.QFrame.Sunken)
        self.separator_line.setObjectName(_fromUtf8("separator_line"))
        self.verticalLayout.addWidget(self.separator_line)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.command_buttons_frame = QtGui.QFrame(controller_view)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.command_buttons_frame.sizePolicy().hasHeightForWidth())
        self.command_buttons_frame.setSizePolicy(sizePolicy)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(90, 90, 90))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(90, 90, 90))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(90, 90, 90))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(90, 90, 90))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        self.command_buttons_frame.setPalette(palette)
        self.command_buttons_frame.setAutoFillBackground(True)
        self.command_buttons_frame.setFrameShape(QtGui.QFrame.NoFrame)
        self.command_buttons_frame.setFrameShadow(QtGui.QFrame.Raised)
        self.command_buttons_frame.setLineWidth(0)
        self.command_buttons_frame.setObjectName(_fromUtf8("command_buttons_frame"))
        self.gridLayout = QtGui.QGridLayout(self.command_buttons_frame)
        self.gridLayout.setMargin(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.load_last_config_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.load_last_config_button.sizePolicy().hasHeightForWidth())
        self.load_last_config_button.setSizePolicy(sizePolicy)
        self.load_last_config_button.setMinimumSize(QtCore.QSize(60, 60))
        self.load_last_config_button.setAutoFillBackground(True)
        self.load_last_config_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.load_last_config_button.setAutoRaise(True)
        self.load_last_config_button.setObjectName(_fromUtf8("load_last_config_button"))
        self.gridLayout.addWidget(self.load_last_config_button, 0, 1, 1, 1)
        self.load_config_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.load_config_button.sizePolicy().hasHeightForWidth())
        self.load_config_button.setSizePolicy(sizePolicy)
        self.load_config_button.setMinimumSize(QtCore.QSize(60, 60))
        self.load_config_button.setAutoFillBackground(True)
        self.load_config_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.load_config_button.setAutoRaise(True)
        self.load_config_button.setObjectName(_fromUtf8("load_config_button"))
        self.gridLayout.addWidget(self.load_config_button, 0, 0, 1, 1)
        self.add_sensor_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.add_sensor_button.sizePolicy().hasHeightForWidth())
        self.add_sensor_button.setSizePolicy(sizePolicy)
        self.add_sensor_button.setMinimumSize(QtCore.QSize(60, 60))
        self.add_sensor_button.setAutoFillBackground(True)
        self.add_sensor_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.add_sensor_button.setAutoRaise(True)
        self.add_sensor_button.setObjectName(_fromUtf8("add_sensor_button"))
        self.gridLayout.addWidget(self.add_sensor_button, 1, 0, 1, 1)
        self.remove_sensors_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.remove_sensors_button.sizePolicy().hasHeightForWidth())
        self.remove_sensors_button.setSizePolicy(sizePolicy)
        self.remove_sensors_button.setMinimumSize(QtCore.QSize(60, 60))
        self.remove_sensors_button.setAutoFillBackground(True)
        self.remove_sensors_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.remove_sensors_button.setAutoRaise(True)
        self.remove_sensors_button.setObjectName(_fromUtf8("remove_sensors_button"))
        self.gridLayout.addWidget(self.remove_sensors_button, 1, 1, 1, 1)
        self.save_config_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.save_config_button.sizePolicy().hasHeightForWidth())
        self.save_config_button.setSizePolicy(sizePolicy)
        self.save_config_button.setMinimumSize(QtCore.QSize(60, 60))
        self.save_config_button.setAutoFillBackground(True)
        self.save_config_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.save_config_button.setAutoRaise(True)
        self.save_config_button.setObjectName(_fromUtf8("save_config_button"))
        self.gridLayout.addWidget(self.save_config_button, 0, 2, 1, 1)
        self.select_sources_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.select_sources_button.sizePolicy().hasHeightForWidth())
        self.select_sources_button.setSizePolicy(sizePolicy)
        self.select_sources_button.setMinimumSize(QtCore.QSize(60, 60))
        self.select_sources_button.setAutoFillBackground(True)
        self.select_sources_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.select_sources_button.setAutoRaise(True)
        self.select_sources_button.setObjectName(_fromUtf8("select_sources_button"))
        self.gridLayout.addWidget(self.select_sources_button, 1, 2, 1, 1)
        self.messages_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.messages_button.sizePolicy().hasHeightForWidth())
        self.messages_button.setSizePolicy(sizePolicy)
        self.messages_button.setMinimumSize(QtCore.QSize(60, 60))
        self.messages_button.setAutoFillBackground(True)
        self.messages_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.messages_button.setAutoRaise(True)
        self.messages_button.setObjectName(_fromUtf8("messages_button"))
        self.gridLayout.addWidget(self.messages_button, 2, 0, 1, 1)
        self.add_controller_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.add_controller_button.sizePolicy().hasHeightForWidth())
        self.add_controller_button.setSizePolicy(sizePolicy)
        self.add_controller_button.setMinimumSize(QtCore.QSize(60, 60))
        self.add_controller_button.setAutoFillBackground(True)
        self.add_controller_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.add_controller_button.setAutoRaise(True)
        self.add_controller_button.setObjectName(_fromUtf8("add_controller_button"))
        self.gridLayout.addWidget(self.add_controller_button, 3, 0, 1, 1)
        self.issues_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.issues_button.sizePolicy().hasHeightForWidth())
        self.issues_button.setSizePolicy(sizePolicy)
        self.issues_button.setMinimumSize(QtCore.QSize(60, 60))
        self.issues_button.setAutoFillBackground(True)
        self.issues_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.issues_button.setAutoRaise(True)
        self.issues_button.setObjectName(_fromUtf8("issues_button"))
        self.gridLayout.addWidget(self.issues_button, 2, 1, 1, 1)
        self.settings_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.settings_button.sizePolicy().hasHeightForWidth())
        self.settings_button.setSizePolicy(sizePolicy)
        self.settings_button.setMinimumSize(QtCore.QSize(60, 60))
        self.settings_button.setAutoFillBackground(True)
        self.settings_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.settings_button.setAutoRaise(True)
        self.settings_button.setObjectName(_fromUtf8("settings_button"))
        self.gridLayout.addWidget(self.settings_button, 2, 2, 1, 1)
        self.help_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.help_button.sizePolicy().hasHeightForWidth())
        self.help_button.setSizePolicy(sizePolicy)
        self.help_button.setMinimumSize(QtCore.QSize(60, 60))
        self.help_button.setAutoFillBackground(True)
        self.help_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.help_button.setAutoRaise(True)
        self.help_button.setObjectName(_fromUtf8("help_button"))
        self.gridLayout.addWidget(self.help_button, 3, 2, 1, 1)
        self.view_sensor_data_button = QtGui.QToolButton(self.command_buttons_frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.view_sensor_data_button.sizePolicy().hasHeightForWidth())
        self.view_sensor_data_button.setSizePolicy(sizePolicy)
        self.view_sensor_data_button.setMinimumSize(QtCore.QSize(60, 60))
        self.view_sensor_data_button.setAutoFillBackground(True)
        self.view_sensor_data_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.view_sensor_data_button.setAutoRaise(True)
        self.view_sensor_data_button.setObjectName(_fromUtf8("view_sensor_data_button"))
        self.gridLayout.addWidget(self.view_sensor_data_button, 3, 1, 1, 1)
        self.horizontalLayout_3.addWidget(self.command_buttons_frame)
        spacerItem8 = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem8)
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.stacked_group_box = QtGui.QGroupBox(controller_view)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.stacked_group_box.setFont(font)
        self.stacked_group_box.setAlignment(QtCore.Qt.AlignCenter)
        self.stacked_group_box.setObjectName(_fromUtf8("stacked_group_box"))
        self.gridLayout_2 = QtGui.QGridLayout(self.stacked_group_box)
        self.gridLayout_2.setMargin(3)
        self.gridLayout_2.setSpacing(3)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.stacked_widget = QtGui.QStackedWidget(self.stacked_group_box)
        self.stacked_widget.setObjectName(_fromUtf8("stacked_widget"))
        self.page = QtGui.QWidget()
        self.page.setObjectName(_fromUtf8("page"))
        self.stacked_widget.addWidget(self.page)
        self.page_2 = QtGui.QWidget()
        self.page_2.setObjectName(_fromUtf8("page_2"))
        self.stacked_widget.addWidget(self.page_2)
        self.gridLayout_2.addWidget(self.stacked_widget, 0, 0, 1, 1)
        self.verticalLayout_2.addWidget(self.stacked_group_box)
        self.horizontalLayout_3.addLayout(self.verticalLayout_2)
        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.retranslateUi(controller_view)
        QtCore.QMetaObject.connectSlotsByName(controller_view)

    def retranslateUi(self, controller_view):
        controller_view.setWindowTitle(_translate("controller_view", "Form", None))
        self.controller_title.setText(_translate("controller_view", "Main Menu", None))
        self.session_status_label_fixed.setText(_translate("controller_view", "Session:", None))
        self.session_status_label.setText(_translate("controller_view", "<status>", None))
        self.setup_sensors_button.setText(_translate("controller_view", "Setup", None))
        self.start_button.setText(_translate("controller_view", "Start", None))
        self.pause_button.setText(_translate("controller_view", "Pause", None))
        self.notes_button.setText(_translate("controller_view", "Notes", None))
        self.end_button.setText(_translate("controller_view", "End", None))
        self.load_last_config_button.setText(_translate("controller_view", "Load Last", None))
        self.load_config_button.setText(_translate("controller_view", "Load Config", None))
        self.add_sensor_button.setText(_translate("controller_view", "Add Sensor", None))
        self.remove_sensors_button.setText(_translate("controller_view", "Remove Sensor", None))
        self.save_config_button.setText(_translate("controller_view", "Save Config", None))
        self.select_sources_button.setText(_translate("controller_view", "Select Sources", None))
        self.messages_button.setText(_translate("controller_view", "Messages", None))
        self.add_controller_button.setText(_translate("controller_view", "Add Controller", None))
        self.issues_button.setText(_translate("controller_view", "Issues", None))
        self.settings_button.setText(_translate("controller_view", "Settings", None))
        self.help_button.setText(_translate("controller_view", "Help", None))
        self.view_sensor_data_button.setText(_translate("controller_view", "Sensor Data", None))
        self.stacked_group_box.setTitle(_translate("controller_view", "Settings", None))
