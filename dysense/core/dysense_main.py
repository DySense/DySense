#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import threading

import zmq

# Automatically convert QString to unicode (in python 2.7)
# and use default python types instead of QVariant.
# This will change API for entire app.
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4 import QtGui, Qt

from dysense.gui.dysense_main_window import DysenseMainWindow
from dysense.gui.gui_presenter import GUIPresenter
from dysense.gui.except_hook import excepthook

from dysense.core.controller_manager import ControllerManager
from dysense.core.sensor_controller import SensorController
from dysense.core.utility import yaml_load_unicode, make_unicode, show_window_at_best_size
from dysense.core.version import *

from dysense.interfaces.server_interface import ServerInterface
from dysense.interfaces.client_interface import ClientInterface

def dysense_main():

    # This program uses relative paths for finding sensors, so make sure the working directory
    # is set to the directory containing this function.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    app = QtGui.QApplication(sys.argv)
    #app.setStyle('plastique')
    app.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))

    # Tell system to call our custom function when an unhandled exception occurs
    sys.excepthook = excepthook

    # Time is treated as a double-precision floating point number which should always be true.
    # If for some reason it's not then notify a user that all times will be incorrect.
    max_required_precision = 1e-13
    if sys.float_info.epsilon > max_required_precision:
        raise Exception('System doesn\'t support required precision. Time\'s will not be correct.')

    if os.name == 'nt':
        # If running on windows then need to unassociate process from python so that
        # the OS will show the correct icon in the taskbar.
        import ctypes
        myappid = 'dysense.main.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    zmq_context = zmq.Context()

    # Load sensor metadata
    with open("../metadata/sensor_metadata.yaml", 'r') as stream:
        sensor_metadata = yaml_load_unicode(stream)

    # Servers for controllers to talk to sensors and managers.
    # e.g. "c2s_server" means controller to sensors.
    # Manager server needs to bind on all address since it could receive connections from other computers.
    c2s_server = ServerInterface(zmq_context, 'controller', 'c2s', s2c_version, ports=range(60110, 60120), all_addresses=False)
    c2m_server = ServerInterface(zmq_context, 'controller', 'c2m', m2c_version, ports=range(60120, 60130), all_addresses=True)

    # Server for manager to talk to presenters, and client so managers can talk to controllers.
    m2p_server = ServerInterface(zmq_context, 'manager', p2m_version, 'm2p', ports=None)
    m2c_client = ClientInterface(zmq_context, 'manager', m2c_version)

    # Client for presenter to talk to managers.
    p2m_client = ClientInterface(zmq_context, 'gui_presenter', p2m_version)

    # Wire clients to servers so that when they are setup they will automatically connect.
    m2c_client.wire_locally_to(c2m_server)
    p2m_client.wire_locally_to(m2p_server)

    # Configure system.
    controller_manager = ControllerManager(m2c_client, m2p_server)
    gui_presenter = GUIPresenter(p2m_client, sensor_metadata)
    main_window = DysenseMainWindow(gui_presenter, sensor_metadata['sensors'])
    sensor_controller = SensorController(zmq_context, sensor_metadata, main_window.local_controller_name, c2s_server, c2m_server)

    gui_presenter.setup_view(main_window)

    # Start up component threads.
    controller_manager_thread = threading.Thread(target=controller_manager.run)
    sensor_controller_thread = threading.Thread(target=sensor_controller.run)
    controller_manager_thread.start()
    sensor_controller_thread.start()

    gui_presenter.add_controller(c2m_server.local_endpoint, sensor_controller.controller_id)
    gui_presenter.receive_messages()

    try:
        show_window_at_best_size(main_window)
        app.exec_()
    finally:
        sensor_controller.stop_request.set()
        sensor_controller_thread.join()
        controller_manager.stop_request.set()
        controller_manager_thread.join()
        gui_presenter.close()
        app.exit()

if __name__ == '__main__':

    # Run dysense with the default arguments.
    dysense_main()

