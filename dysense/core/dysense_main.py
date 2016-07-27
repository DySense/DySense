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

from PyQt4 import QtGui

from dysense.gui.dysense_main_window import DysenseMainWindow
from dysense.gui.gui_presenter import GUIPresenter
from dysense.gui.except_hook import excepthook

from dysense.core.controller_manager import ControllerManager
from dysense.core.sensor_controller import SensorController
from dysense.core.utility import yaml_load_unicode, make_unicode

def dysense_main(use_gui=True, use_webservice=False, config_filepath='', debug=False):
        
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
    
    # Configure system.
    controller_manager = ControllerManager(zmq_context)
    gui_presenter = GUIPresenter(zmq_context, controller_manager, sensor_metadata)
    main_window = DysenseMainWindow(gui_presenter, sensor_metadata['sensors'])   
    sensor_controller = SensorController(zmq_context, sensor_metadata, main_window.local_controller_name)
    
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
        #main_window.showMaximized()
        main_window.show()
        app.exec_()
    
        # TODO intercept window closing event and if there are any non-closed sensors
        # on the local controller then popup a yes-no dialog window telling user that if
        # they quit then resources might not be released. 
        
        # TODO show a 'closing dialog' until these next lines complete in case they hang.
    
    finally:
        # Close down system from bottom to top since data will be flowing that way.
        sensor_controller.stop_request.set()
        sensor_controller_thread.join()
        controller_manager.stop_request.set()
        controller_manager_thread.join()
        gui_presenter.close()
        
if __name__ == '__main__':
        
    # Run dysense with the default arguments.
    dysense_main()
    