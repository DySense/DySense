#!/usr/bin/env python

import threading
import zmq
import sys
import yaml
import os

#from test_window import TestWindow #for use with test window
from dysense_main_window import DysenseMainWindow #for use with new main window
from main_presenter import MainPresenter
from controller_manager import ControllerManager
from sensor_controller import SensorController
from except_hook import excepthook
from PyQt4 import QtGui

if __name__ == '__main__':
        
    app = QtGui.QApplication(sys.argv)
    app.setStyle('plastique')
    app.setWindowIcon(QtGui.QIcon('../resources/dysense_logo_no_text.png'))
    
    # Tell system to call our custom function when an unhandled exception occurs
    sys.excepthook = excepthook    

    if os.name == 'nt':
        # If running on windows then need to unassociate process from python so that
        # the OS will show the correct icon in the taskbar.
        import ctypes
        myappid = u'dysense.ui.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)        

    zmq_context = zmq.Context()

    # Load metadata before adding any controllers so can verify version.
    with open("../metadata/sensor_metadata.yaml", 'r') as stream:
        sensor_metadata = yaml.load(stream)
        
    # Configure system.
    controller_manager = ControllerManager(zmq_context)
    main_presenter = MainPresenter(zmq_context, controller_manager, sensor_metadata)
    main_window = DysenseMainWindow(main_presenter)
    sensor_controller = SensorController(zmq_context, sensor_metadata, main_window.local_controller_name)
    
    main_presenter.setup_view(main_window)
    
    # Tell presenter how to connect to manager.
    main_presenter.connect_endpoint(controller_manager.presenter_local_endpoint)
    
    # Start up component threads.
    controller_manager_thread = threading.Thread(target=controller_manager.run)
    sensor_controller_thread = threading.Thread(target=sensor_controller.run)
    controller_manager_thread.start()
    sensor_controller_thread.start()
    
    # Must do this after starting up threads so socket has a peer to connect with.
    main_presenter.add_controller(sensor_controller.manager_local_endpoint, 'this_computer')
    main_presenter.receive_messages()
    
    try:
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
        main_presenter.close()
    