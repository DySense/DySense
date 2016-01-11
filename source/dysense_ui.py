#!/usr/bin/env python

import threading
import zmq
import sys
import yaml

from test_window import TestWindow
from main_presenter import MainPresenter
from controller_manager import ControllerManager
from sensor_controller import SensorController

from PyQt4 import QtGui

if __name__ == '__main__':
        
    app = QtGui.QApplication(sys.argv)
    
    zmq_context = zmq.Context()
    
    # Load metadata before adding any controllers so can verify version.
    with open("../metadata/sensor_metadata.yaml", 'r') as stream:
        sensor_metadata = yaml.load(stream)

    # Configure system.
    sensor_controller = SensorController(zmq_context, sensor_metadata)
    controller_manager = ControllerManager(zmq_context)
    main_presenter = MainPresenter(zmq_context, controller_manager, sensor_metadata)
    main_window = TestWindow(main_presenter)
    main_presenter.view = main_window
    
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
    
    main_window.show()
    app.exec_()
    
    # TODO intercept window closing event and if there are any non-closed sensors
    # on the local controller then popup a yes-no dialog window telling user that if
    # they quit then resources might not be released. 
    
    # TODO show a 'closing dialog' until these next lines complete in case they hang.
    
    # Close down system from bottom to top since data will be flowing that way.
    sensor_controller.stop_request.set()
    sensor_controller_thread.join()
    controller_manager.stop_request.set()
    controller_manager_thread.join()
    main_presenter.close()
    