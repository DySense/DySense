#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import threading
import zmq
import sys
import yaml
import os

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
from dysense.core.utility import yaml_load_unicode, make_unicode

from dysense.interfaces.server_interface import ServerInterface
from dysense.interfaces.client_interface import ClientInterface

def dysense_main(use_gui=True, use_webservice=False, config_filepath='', debug=False):
    
    # This program uses relative paths for finding sensors, so make sure the working directory
    # is set to the directory containing this function.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
    app = QtGui.QApplication(sys.argv)
    #app.setStyle('plastique')
    app.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
    
    # Tell system to call our custom function when an unhandled exception occurs
    sys.excepthook = excepthook

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

    # Servers for controllers to talk to sensors and managers
    c2s_server = ServerInterface(zmq_context, 'controller', 'c2s', ports=range(60110, 60120), all_addresses=False)
    #c2m_server = ServerInterface(client='manager', server='controller', ports=range(60120, 60130), all_addresses=True)
    
    # Server for manager to talk to presenters, and client so managers can talk to controllers.
    #m2p_server = ServerInterface(client='presenter', server='manager', ports=None)
    #m2c_client = ClientInterface(c2m_server.local_endpoint)
    
    # Client for presenter to talk to managers.
    #p2m_client = ClientInterface(m2p_server.local_endpoint)

    # Configure system.
    controller_manager = ControllerManager(zmq_context)
    gui_presenter = GUIPresenter(zmq_context, controller_manager, sensor_metadata)
    main_window = DysenseMainWindow(gui_presenter, sensor_metadata['sensors'])   
    sensor_controller = SensorController(zmq_context, sensor_metadata, main_window.local_controller_name, c2s_server)
    
    gui_presenter.setup_view(main_window)
    
    # Tell presenter how to connect to manager.
    gui_presenter.connect_endpoint(controller_manager.presenter_local_endpoint)
    
    # Start up component threads.
    controller_manager_thread = threading.Thread(target=controller_manager.run)
    sensor_controller_thread = threading.Thread(target=sensor_controller.run)
    controller_manager_thread.start()
    sensor_controller_thread.start()
    
    # Must do this after starting up threads so socket has a peer to connect with.
    gui_presenter.add_controller(sensor_controller.manager_local_endpoint, 'this_computer')
    gui_presenter.receive_messages()
    
    try:

        # Set main window size based off screen size.  If screen size is small then maximize window from start.
        screen_size = QtGui.QDesktopWidget().availableGeometry(main_window)
        if screen_size.width() <= 800 or screen_size.height() <= 600:
            main_window.showMaximized()
        else:
            if screen_size.width() > screen_size.height():
                # Base desired width on height because GUI looks best square-ish.
                # Use 'max' since we don't want to make window smaller than it wants to be.
                desired_height = max(screen_size.height() * 0.75, main_window.height())
                desired_width = max(desired_height * 1.2, main_window.width())
                # Don't let width get bigger than screen.
                desired_width = min(desired_width, screen_size.width())
            else: 
                # On a 'tall' screen (probably rotated). Makes sense to base height on width.
                desired_width = max(screen_size.width() * 0.9, main_window.width())
                desired_height = max(desired_width * 0.83, main_window.height())
                # Don't let height get bigger than screen.
                desired_height = min(desired_height, screen_size.height())
            
            main_window.resize(Qt.QSize(desired_width, desired_height))
            main_window.show()

        app.exec_()
    
    finally:

        sensor_controller.stop_request.set()
        sensor_controller_thread.join()
        controller_manager.stop_request.set()
        controller_manager_thread.join()
        gui_presenter.close()
        
if __name__ == '__main__':
        
    # Run dysense with the default arguments.
    dysense_main()
    