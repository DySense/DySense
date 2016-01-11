#!/usr/bin/env python

import time
import os
import logging
import sys
import threading
import subprocess

# Import python sensor classes that are started as threads.
from sensors.irt_ue import IRT_UE
from sensors.test import TestSensor

def create_sensor(sensor_type, sensor_id, sensor_settings, context, local_endpoint, remote_endpoint):
    '''
    '''
    sensor = None
    
    # TODO support remote sensors
    startup_args = (sensor_id, sensor_settings, context, local_endpoint)
    
    if sensor_type == 'irt_ue':
        sensor = create_thread(IRT_UE, startup_args)
    if sensor_type == 'test':
        sensor = create_thread(TestSensor, startup_args)
    
    return sensor

def create_thread(class_name, startup_args):
    
    sensor = class_name(*startup_args)
    
    # We want it to be a daemon thread so it doesn't keep the process from closing.
    sensor_thread = threading.Thread(target=sensor.run)
    sensor_thread.setDaemon(True)
    sensor_thread.start()
    return sensor_thread
    
def create_process(relative_path, startup_args):
    
    absolute_path = os.path.join(os.path.abspath(sys.path[0]), relative_path)

    # The os.setsid() is passed in the argument preexec_fn so
    # it's run after the fork() and before  exec() to run the shell
    sensor_process = subprocess.Popen([absolute_path, ' '.join(startup_args)], shell=False)
    
    return sensor_process
    