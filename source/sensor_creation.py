#!/usr/bin/env python

import time
import os
import logging
import sys
import threading
import subprocess
import json

def create_sensor(sensor_type, sensor_id, sensor_settings, context, local_endpoint, remote_endpoint):
    '''
    '''
    sensor = None
    
    local_startup_args = [sensor_id, sensor_settings, context, local_endpoint]
    remote_startup_args = [sensor_id, sensor_settings, remote_endpoint]
    
    # Use local imports for threads in case they have dependencies that other users don't care about.
    if sensor_type == 'irt_ue':
        from sensors.irt_ue import IRT_UE
        sensor = create_thread(IRT_UE, local_startup_args)
    if sensor_type == 'test':
        from sensors.test import TestSensor
        sensor = create_thread(TestSensor, local_startup_args)
        #sensor = create_process('../sensors/test.py', remote_startup_args, True)
    if sensor_type == 'kinectv2_msdk':
        pass
    
    return sensor

def create_thread(class_name, startup_args):
    
    sensor = class_name(*startup_args)
    
    # We want it to be a daemon thread so it doesn't keep the process from closing.
    sensor_thread = threading.Thread(target=sensor.run)
    sensor_thread.setDaemon(True)
    sensor_thread.start()
    return sensor_thread
    
def create_process(relative_path, startup_args, python=False):
    
    startup_args[0] = str(startup_args[0]) # make sure ID is a string.
    startup_args[1] = json.dumps(startup_args[1]) # serialize sensor settings

    absolute_path = os.path.join(os.path.abspath(sys.path[0]), relative_path)
    try:
        if not python:
            sensor_process = subprocess.Popen([absolute_path] + startup_args, shell=False)
        else:
            # Need to include sys.executable when using python.
            sensor_process = subprocess.Popen([sys.executable, absolute_path] + startup_args, shell=False)
    except WindowsError as e:
        print absolute_path
        raise
            
    return sensor_process
    