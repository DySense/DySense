# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dysense_designer.ui'
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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(1299, 873)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setEnabled(True)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_7 = QtGui.QHBoxLayout()
        self.horizontalLayout_7.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.horizontalLayout_7.setContentsMargins(-1, -1, -1, 0)
        self.horizontalLayout_7.setObjectName(_fromUtf8("horizontalLayout_7"))
        self.logo_label = QtGui.QLabel(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.logo_label.sizePolicy().hasHeightForWidth())
        self.logo_label.setSizePolicy(sizePolicy)
        self.logo_label.setMinimumSize(QtCore.QSize(140, 40))
        self.logo_label.setMaximumSize(QtCore.QSize(140, 40))
        self.logo_label.setText(_fromUtf8(""))
        self.logo_label.setObjectName(_fromUtf8("logo_label"))
        self.horizontalLayout_7.addWidget(self.logo_label)
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.horizontalLayout_7.addLayout(self.gridLayout)
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        spacerItem = QtGui.QSpacerItem(30, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem)
        self.session_label = QtGui.QLabel(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(18)
        font.setBold(True)
        font.setWeight(75)
        self.session_label.setFont(font)
        self.session_label.setObjectName(_fromUtf8("session_label"))
        self.horizontalLayout_5.addWidget(self.session_label)
        self.session_value_label = QtGui.QLabel(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.session_value_label.sizePolicy().hasHeightForWidth())
        self.session_value_label.setSizePolicy(sizePolicy)
        self.session_value_label.setMinimumSize(QtCore.QSize(125, 0))
        font = QtGui.QFont()
        font.setPointSize(17)
        self.session_value_label.setFont(font)
        self.session_value_label.setText(_fromUtf8(""))
        self.session_value_label.setObjectName(_fromUtf8("session_value_label"))
        self.horizontalLayout_5.addWidget(self.session_value_label)
        self.main_status_label = QtGui.QLabel(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(18)
        font.setBold(True)
        font.setWeight(75)
        self.main_status_label.setFont(font)
        self.main_status_label.setObjectName(_fromUtf8("main_status_label"))
        self.horizontalLayout_5.addWidget(self.main_status_label)
        self.main_status_value_label = QtGui.QLabel(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.main_status_value_label.sizePolicy().hasHeightForWidth())
        self.main_status_value_label.setSizePolicy(sizePolicy)
        self.main_status_value_label.setMinimumSize(QtCore.QSize(120, 0))
        font = QtGui.QFont()
        font.setPointSize(17)
        self.main_status_value_label.setFont(font)
        self.main_status_value_label.setText(_fromUtf8(""))
        self.main_status_value_label.setObjectName(_fromUtf8("main_status_value_label"))
        self.horizontalLayout_5.addWidget(self.main_status_value_label)
        self.horizontalLayout_7.addLayout(self.horizontalLayout_5)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem1)
        self.menu_button = QtGui.QPushButton(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.menu_button.sizePolicy().hasHeightForWidth())
        self.menu_button.setSizePolicy(sizePolicy)
        self.menu_button.setMinimumSize(QtCore.QSize(260, 0))
        font = QtGui.QFont()
        font.setPointSize(19)
        font.setBold(True)
        font.setWeight(75)
        self.menu_button.setFont(font)
        self.menu_button.setObjectName(_fromUtf8("menu_button"))
        self.horizontalLayout_7.addWidget(self.menu_button)
        self.verticalLayout.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.sensor_list_widget = QtGui.QListWidget(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(16)
        self.sensor_list_widget.setFont(font)
        self.sensor_list_widget.setObjectName(_fromUtf8("sensor_list_widget"))
        self.horizontalLayout_2.addWidget(self.sensor_list_widget)
        spacerItem2 = QtGui.QSpacerItem(30, 20, QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem2)
        self.gridLayout_2 = QtGui.QGridLayout()
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.stacked_widget = QtGui.QStackedWidget(self.centralwidget)
        self.stacked_widget.setObjectName(_fromUtf8("stacked_widget"))
        self.menu_page = QtGui.QWidget()
        self.menu_page.setObjectName(_fromUtf8("menu_page"))
        self.gridLayout_3 = QtGui.QGridLayout(self.menu_page)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.main_message_center_text_edit = QtGui.QTextEdit(self.menu_page)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.main_message_center_text_edit.setFont(font)
        self.main_message_center_text_edit.setObjectName(_fromUtf8("main_message_center_text_edit"))
        self.gridLayout_3.addWidget(self.main_message_center_text_edit, 10, 1, 1, 1)
        self.message_center_label = QtGui.QLabel(self.menu_page)
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.message_center_label.setFont(font)
        self.message_center_label.setAlignment(QtCore.Qt.AlignCenter)
        self.message_center_label.setObjectName(_fromUtf8("message_center_label"))
        self.gridLayout_3.addWidget(self.message_center_label, 4, 1, 1, 1)
        self.horizontalLayout_6 = QtGui.QHBoxLayout()
        self.horizontalLayout_6.setObjectName(_fromUtf8("horizontalLayout_6"))
        self.settings_group_box = QtGui.QGroupBox(self.menu_page)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.settings_group_box.setFont(font)
        self.settings_group_box.setAlignment(QtCore.Qt.AlignCenter)
        self.settings_group_box.setObjectName(_fromUtf8("settings_group_box"))
        self.gridLayout_4 = QtGui.QGridLayout(self.settings_group_box)
        self.gridLayout_4.setObjectName(_fromUtf8("gridLayout_4"))
        self.label = QtGui.QLabel(self.settings_group_box)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout_4.addWidget(self.label, 1, 0, 1, 1)
        self.platform_name_label = QtGui.QLabel(self.settings_group_box)
        self.platform_name_label.setObjectName(_fromUtf8("platform_name_label"))
        self.gridLayout_4.addWidget(self.platform_name_label, 3, 0, 1, 1)
        self.platform_id_line_edit = QtGui.QLineEdit(self.settings_group_box)
        self.platform_id_line_edit.setObjectName(_fromUtf8("platform_id_line_edit"))
        self.gridLayout_4.addWidget(self.platform_id_line_edit, 4, 1, 1, 1)
        self.platform_id_label = QtGui.QLabel(self.settings_group_box)
        self.platform_id_label.setObjectName(_fromUtf8("platform_id_label"))
        self.gridLayout_4.addWidget(self.platform_id_label, 4, 0, 1, 1)
        self.experiment_id_label = QtGui.QLabel(self.settings_group_box)
        self.experiment_id_label.setObjectName(_fromUtf8("experiment_id_label"))
        self.gridLayout_4.addWidget(self.experiment_id_label, 5, 0, 1, 1)
        self.surveyed_check_box = QtGui.QCheckBox(self.settings_group_box)
        self.surveyed_check_box.setObjectName(_fromUtf8("surveyed_check_box"))
        self.gridLayout_4.addWidget(self.surveyed_check_box, 6, 1, 1, 1)
        self.experiment_id_line_edit = QtGui.QLineEdit(self.settings_group_box)
        self.experiment_id_line_edit.setObjectName(_fromUtf8("experiment_id_line_edit"))
        self.gridLayout_4.addWidget(self.experiment_id_line_edit, 5, 1, 1, 1)
        self.platform_name_line_edit = QtGui.QLineEdit(self.settings_group_box)
        self.platform_name_line_edit.setObjectName(_fromUtf8("platform_name_line_edit"))
        self.gridLayout_4.addWidget(self.platform_name_line_edit, 3, 1, 1, 1)
        self.operator_name_label = QtGui.QLabel(self.settings_group_box)
        self.operator_name_label.setObjectName(_fromUtf8("operator_name_label"))
        self.gridLayout_4.addWidget(self.operator_name_label, 2, 0, 1, 1)
        self.operator_name_line_edit = QtGui.QLineEdit(self.settings_group_box)
        self.operator_name_line_edit.setObjectName(_fromUtf8("operator_name_line_edit"))
        self.gridLayout_4.addWidget(self.operator_name_line_edit, 2, 1, 1, 1)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.output_directory_line_edit = QtGui.QLineEdit(self.settings_group_box)
        self.output_directory_line_edit.setObjectName(_fromUtf8("output_directory_line_edit"))
        self.horizontalLayout_4.addWidget(self.output_directory_line_edit)
        self.output_directory_tool_button = QtGui.QToolButton(self.settings_group_box)
        self.output_directory_tool_button.setObjectName(_fromUtf8("output_directory_tool_button"))
        self.horizontalLayout_4.addWidget(self.output_directory_tool_button)
        self.gridLayout_4.addLayout(self.horizontalLayout_4, 1, 1, 1, 1)
        self.controller_name_label = QtGui.QLabel(self.settings_group_box)
        self.controller_name_label.setObjectName(_fromUtf8("controller_name_label"))
        self.gridLayout_4.addWidget(self.controller_name_label, 0, 0, 1, 1)
        self.controller_name_line_edit = QtGui.QLineEdit(self.settings_group_box)
        self.controller_name_line_edit.setObjectName(_fromUtf8("controller_name_line_edit"))
        self.gridLayout_4.addWidget(self.controller_name_line_edit, 0, 1, 1, 1)
        self.horizontalLayout_6.addWidget(self.settings_group_box)
        self.sensor_controls_group_box = QtGui.QGroupBox(self.menu_page)
        font = QtGui.QFont()
        font.setPointSize(15)
        self.sensor_controls_group_box.setFont(font)
        self.sensor_controls_group_box.setAlignment(QtCore.Qt.AlignCenter)
        self.sensor_controls_group_box.setObjectName(_fromUtf8("sensor_controls_group_box"))
        self.formLayout = QtGui.QFormLayout(self.sensor_controls_group_box)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.sensor_controls_label_1 = QtGui.QLabel(self.sensor_controls_group_box)
        self.sensor_controls_label_1.setObjectName(_fromUtf8("sensor_controls_label_1"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.sensor_controls_label_1)
        self.sensor_controls_label_2 = QtGui.QLabel(self.sensor_controls_group_box)
        self.sensor_controls_label_2.setObjectName(_fromUtf8("sensor_controls_label_2"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.sensor_controls_label_2)
        self.sensor_controls_label_3 = QtGui.QLabel(self.sensor_controls_group_box)
        self.sensor_controls_label_3.setObjectName(_fromUtf8("sensor_controls_label_3"))
        self.formLayout.setWidget(6, QtGui.QFormLayout.LabelRole, self.sensor_controls_label_3)
        self.close_sensors_button = QtGui.QPushButton(self.sensor_controls_group_box)
        self.close_sensors_button.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(15)
        self.close_sensors_button.setFont(font)
        self.close_sensors_button.setObjectName(_fromUtf8("close_sensors_button"))
        self.formLayout.setWidget(10, QtGui.QFormLayout.FieldRole, self.close_sensors_button)
        self.setup_sensors_button = QtGui.QPushButton(self.sensor_controls_group_box)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.setup_sensors_button.sizePolicy().hasHeightForWidth())
        self.setup_sensors_button.setSizePolicy(sizePolicy)
        self.setup_sensors_button.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(15)
        self.setup_sensors_button.setFont(font)
        self.setup_sensors_button.setObjectName(_fromUtf8("setup_sensors_button"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.setup_sensors_button)
        self.start_session_button = QtGui.QPushButton(self.sensor_controls_group_box)
        self.start_session_button.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(15)
        font.setBold(False)
        font.setWeight(50)
        self.start_session_button.setFont(font)
        self.start_session_button.setObjectName(_fromUtf8("start_session_button"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.start_session_button)
        self.end_session_button = QtGui.QPushButton(self.sensor_controls_group_box)
        self.end_session_button.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(15)
        self.end_session_button.setFont(font)
        self.end_session_button.setObjectName(_fromUtf8("end_session_button"))
        self.formLayout.setWidget(8, QtGui.QFormLayout.FieldRole, self.end_session_button)
        self.pause_sensors_button = QtGui.QPushButton(self.sensor_controls_group_box)
        self.pause_sensors_button.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(15)
        self.pause_sensors_button.setFont(font)
        self.pause_sensors_button.setObjectName(_fromUtf8("pause_sensors_button"))
        self.formLayout.setWidget(6, QtGui.QFormLayout.FieldRole, self.pause_sensors_button)
        self.resume_sensors_button = QtGui.QPushButton(self.sensor_controls_group_box)
        self.resume_sensors_button.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(15)
        self.resume_sensors_button.setFont(font)
        self.resume_sensors_button.setObjectName(_fromUtf8("resume_sensors_button"))
        self.formLayout.setWidget(7, QtGui.QFormLayout.FieldRole, self.resume_sensors_button)
        self.sensor_controls_label_4 = QtGui.QLabel(self.sensor_controls_group_box)
        self.sensor_controls_label_4.setObjectName(_fromUtf8("sensor_controls_label_4"))
        self.formLayout.setWidget(7, QtGui.QFormLayout.LabelRole, self.sensor_controls_label_4)
        self.sensor_controls_label_5 = QtGui.QLabel(self.sensor_controls_group_box)
        self.sensor_controls_label_5.setObjectName(_fromUtf8("sensor_controls_label_5"))
        self.formLayout.setWidget(8, QtGui.QFormLayout.LabelRole, self.sensor_controls_label_5)
        self.sensor_controls_label_6 = QtGui.QLabel(self.sensor_controls_group_box)
        self.sensor_controls_label_6.setObjectName(_fromUtf8("sensor_controls_label_6"))
        self.formLayout.setWidget(10, QtGui.QFormLayout.LabelRole, self.sensor_controls_label_6)
        self.horizontalLayout_6.addWidget(self.sensor_controls_group_box)
        self.configure_sensors_group_box = QtGui.QGroupBox(self.menu_page)
        font = QtGui.QFont()
        font.setPointSize(15)
        self.configure_sensors_group_box.setFont(font)
        self.configure_sensors_group_box.setAlignment(QtCore.Qt.AlignCenter)
        self.configure_sensors_group_box.setObjectName(_fromUtf8("configure_sensors_group_box"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.configure_sensors_group_box)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.config_line_edit = QtGui.QLineEdit(self.configure_sensors_group_box)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.config_line_edit.sizePolicy().hasHeightForWidth())
        self.config_line_edit.setSizePolicy(sizePolicy)
        self.config_line_edit.setMinimumSize(QtCore.QSize(250, 0))
        self.config_line_edit.setObjectName(_fromUtf8("config_line_edit"))
        self.horizontalLayout.addWidget(self.config_line_edit)
        self.select_config_tool_button = QtGui.QToolButton(self.configure_sensors_group_box)
        self.select_config_tool_button.setObjectName(_fromUtf8("select_config_tool_button"))
        self.horizontalLayout.addWidget(self.select_config_tool_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.load_config_button = QtGui.QPushButton(self.configure_sensors_group_box)
        self.load_config_button.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(15)
        self.load_config_button.setFont(font)
        self.load_config_button.setObjectName(_fromUtf8("load_config_button"))
        self.verticalLayout_2.addWidget(self.load_config_button)
        self.save_config_button = QtGui.QPushButton(self.configure_sensors_group_box)
        self.save_config_button.setMinimumSize(QtCore.QSize(0, 40))
        self.save_config_button.setObjectName(_fromUtf8("save_config_button"))
        self.verticalLayout_2.addWidget(self.save_config_button)
        self.add_sensor_button = QtGui.QPushButton(self.configure_sensors_group_box)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.add_sensor_button.sizePolicy().hasHeightForWidth())
        self.add_sensor_button.setSizePolicy(sizePolicy)
        self.add_sensor_button.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(15)
        font.setBold(False)
        font.setWeight(50)
        self.add_sensor_button.setFont(font)
        self.add_sensor_button.setObjectName(_fromUtf8("add_sensor_button"))
        self.verticalLayout_2.addWidget(self.add_sensor_button)
        self.select_sources_button = QtGui.QPushButton(self.configure_sensors_group_box)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.select_sources_button.sizePolicy().hasHeightForWidth())
        self.select_sources_button.setSizePolicy(sizePolicy)
        self.select_sources_button.setMinimumSize(QtCore.QSize(0, 40))
        font = QtGui.QFont()
        font.setPointSize(15)
        font.setBold(False)
        font.setWeight(50)
        self.select_sources_button.setFont(font)
        self.select_sources_button.setObjectName(_fromUtf8("select_sources_button"))
        self.verticalLayout_2.addWidget(self.select_sources_button)
        self.horizontalLayout_6.addWidget(self.configure_sensors_group_box)
        self.gridLayout_3.addLayout(self.horizontalLayout_6, 3, 1, 1, 1)
        spacerItem3 = QtGui.QSpacerItem(20, 10, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.gridLayout_3.addItem(spacerItem3, 1, 1, 1, 1)
        self.horizontalLayout_8 = QtGui.QHBoxLayout()
        self.horizontalLayout_8.setObjectName(_fromUtf8("horizontalLayout_8"))
        self.clear_main_message_center_button = QtGui.QPushButton(self.menu_page)
        self.clear_main_message_center_button.setObjectName(_fromUtf8("clear_main_message_center_button"))
        self.horizontalLayout_8.addWidget(self.clear_main_message_center_button)
        spacerItem4 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem4)
        self.gridLayout_3.addLayout(self.horizontalLayout_8, 11, 1, 1, 1)
        self.stacked_widget.addWidget(self.menu_page)
        self.page_2 = QtGui.QWidget()
        self.page_2.setObjectName(_fromUtf8("page_2"))
        self.stacked_widget.addWidget(self.page_2)
        self.gridLayout_2.addWidget(self.stacked_widget, 0, 0, 1, 1)
        self.horizontalLayout_2.addLayout(self.gridLayout_2)
        self.horizontalLayout_2.setStretch(1, 1)
        self.horizontalLayout_2.setStretch(2, 1)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1299, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.stacked_widget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        MainWindow.setTabOrder(self.operator_name_line_edit, self.platform_name_line_edit)
        MainWindow.setTabOrder(self.platform_name_line_edit, self.platform_id_line_edit)
        MainWindow.setTabOrder(self.platform_id_line_edit, self.experiment_id_line_edit)
        MainWindow.setTabOrder(self.experiment_id_line_edit, self.surveyed_check_box)
        MainWindow.setTabOrder(self.surveyed_check_box, self.setup_sensors_button)
        MainWindow.setTabOrder(self.setup_sensors_button, self.start_session_button)
        MainWindow.setTabOrder(self.start_session_button, self.pause_sensors_button)
        MainWindow.setTabOrder(self.pause_sensors_button, self.resume_sensors_button)
        MainWindow.setTabOrder(self.resume_sensors_button, self.end_session_button)
        MainWindow.setTabOrder(self.end_session_button, self.close_sensors_button)
        MainWindow.setTabOrder(self.close_sensors_button, self.config_line_edit)
        MainWindow.setTabOrder(self.config_line_edit, self.select_config_tool_button)
        MainWindow.setTabOrder(self.select_config_tool_button, self.load_config_button)
        MainWindow.setTabOrder(self.load_config_button, self.save_config_button)
        MainWindow.setTabOrder(self.save_config_button, self.add_sensor_button)
        MainWindow.setTabOrder(self.add_sensor_button, self.main_message_center_text_edit)
        MainWindow.setTabOrder(self.main_message_center_text_edit, self.clear_main_message_center_button)
        MainWindow.setTabOrder(self.clear_main_message_center_button, self.sensor_list_widget)
        MainWindow.setTabOrder(self.sensor_list_widget, self.menu_button)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))
        self.session_label.setText(_translate("MainWindow", "Session:", None))
        self.main_status_label.setText(_translate("MainWindow", "Status:", None))
        self.menu_button.setText(_translate("MainWindow", "MENU", None))
        self.message_center_label.setText(_translate("MainWindow", "Message Center", None))
        self.settings_group_box.setTitle(_translate("MainWindow", "Settings", None))
        self.label.setText(_translate("MainWindow", "Output Directory", None))
        self.platform_name_label.setText(_translate("MainWindow", "Platform Name", None))
        self.platform_id_label.setText(_translate("MainWindow", "Platform ID", None))
        self.experiment_id_label.setText(_translate("MainWindow", "Experiment ID", None))
        self.surveyed_check_box.setText(_translate("MainWindow", "Surveyed", None))
        self.operator_name_label.setText(_translate("MainWindow", "Operator Name", None))
        self.output_directory_tool_button.setText(_translate("MainWindow", "...", None))
        self.controller_name_label.setText(_translate("MainWindow", "Controller Name", None))
        self.sensor_controls_group_box.setTitle(_translate("MainWindow", "Main Actions", None))
        self.sensor_controls_label_1.setText(_translate("MainWindow", "1", None))
        self.sensor_controls_label_2.setText(_translate("MainWindow", "2", None))
        self.sensor_controls_label_3.setText(_translate("MainWindow", "3", None))
        self.close_sensors_button.setText(_translate("MainWindow", "Close Sensors", None))
        self.setup_sensors_button.setText(_translate("MainWindow", "Setup Sensors", None))
        self.start_session_button.setText(_translate("MainWindow", "Start Session", None))
        self.end_session_button.setText(_translate("MainWindow", "End Session", None))
        self.pause_sensors_button.setText(_translate("MainWindow", "Pause Sensors", None))
        self.resume_sensors_button.setText(_translate("MainWindow", "Resume Sensors", None))
        self.sensor_controls_label_4.setText(_translate("MainWindow", "4", None))
        self.sensor_controls_label_5.setText(_translate("MainWindow", "5", None))
        self.sensor_controls_label_6.setText(_translate("MainWindow", "6", None))
        self.configure_sensors_group_box.setTitle(_translate("MainWindow", "Configure Sensors", None))
        self.select_config_tool_button.setText(_translate("MainWindow", "...", None))
        self.load_config_button.setText(_translate("MainWindow", "Load Config File", None))
        self.save_config_button.setText(_translate("MainWindow", "Save Config", None))
        self.add_sensor_button.setText(_translate("MainWindow", "Add Sensor", None))
        self.select_sources_button.setText(_translate("MainWindow", "Select Sources", None))
        self.clear_main_message_center_button.setText(_translate("MainWindow", "Clear Message Center", None))

