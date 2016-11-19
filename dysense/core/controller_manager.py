#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import zmq
import threading
import json
import traceback

from dysense.core.utility import json_dumps_unicode, make_unicode
from dysense.interfaces.component_connection import ComponentConnection

class ControllerConnection(ComponentConnection):
    
    def __init__(self, interface, controller_id):

        super(ControllerConnection, self).__init__(interface, controller_id)

class ControllerManager(object):
    
    def __init__(self, context, controller_interface):
        
        self.context = context
        
        self.controller_interface = controller_interface
        
        self.controllers = []
        self.presenters = []
        
        self.stop_request = threading.Event()
        
        # Endpoint for presenters to connect to.
        self.presenter_local_endpoint = 'inproc://presenters'
        
        # ZMQ sockets aren't threadsafe so need to wait until thread starts to create them.
        self.presenter_socket = None
        
        # Just support a single presenter right now for simplicity.
        self.presenter_id = 1
        
        # Lookup tables of {client_id: router_id} so we can figure out how to address clients.
        self.presenter_router_ids = {}
        
        self.message_callbacks = {  # From Presenters
                                  'add_controller': self.handle_add_controller,
                                  'remove_controller': self.handle_remove_controller,
                                  'forward_to_controller': self.handle_forward_to_controller,

                                   # From Controllers
                                  'entire_controller_update': self.handle_entire_controller_update,
                                  'controller_event': self.handle_controller_event,
                                  'entire_sensor_update': self.handle_entire_sensor_update,
                                  'sensor_changed': self.handle_sensor_changed,
                                  'sensor_removed': self.handle_sensor_removed,
                                  'new_sensor_text': self.handle_new_sensor_text,
                                  'new_sensor_data': self.handle_new_sensor_data,
                                  'error_message': self.handle_error_message,
                                  'new_controller_text': self.handle_new_controller_text,
                                  'new_source_data': self.handle_new_source_data,
                                  }
        
        self.controller_interface.register_callbacks(self.message_callbacks)

    def run(self):

        try:
            self.run_message_loop()
        except Exception as e:
            formatted_lines = traceback.format_exc().splitlines()
            traceback_lines = formatted_lines[:-1] 

            error_lines = []
            error_lines.append("------------")
            error_lines.append("{} - {}".format(type(e).__name__, make_unicode(e)))
            for traceback_line in traceback_lines:
                error_lines.append(traceback_line)
            error_lines.append("------------")
                
            # Notify everyone that this manager crashed.
            # TODO this isn't really a controller event
            self.handle_controller_event(self.controllers[0], 'manager_crashed', error_lines)
        finally:
            self.close_down()

    def close_down(self):
        
        self.controller_interface.close()
            
        if self.presenter_socket:
            self.presenter_socket.close()
    
    def run_message_loop(self):
        
        self.presenter_socket = self.context.socket(zmq.ROUTER)
        self.presenter_socket.bind(self.presenter_local_endpoint)
    
        # Amount of time to wait for new messages before timing out.
        message_timeout = 1000 # milliseconds
    
        # Use a poller to receive from multiple interfaces, and to allow timeouts when waiting.
        # Note this must be done BEFORE setting up interfaces so that sockets will get registered correctly.
        self.poller = zmq.Poller()
        self.controller_interface.register_poller(self.poller)
        
        self.controller_interface.setup()
        
        self.poller.register(self.presenter_socket, zmq.POLLIN)
    
        while True:
            
            if self.stop_request.is_set():
                break  # from main loop
            
            self.process_new_messages(message_timeout)

            for controller in self.controllers:
                if controller.connection_state == 'timed_out':
                    # TODO Notify UI and close down controller.
                    pass
            
    def process_new_messages(self, timeout):
        
        # Block until a new message is waiting or timeout occurs.
        msgs = dict(self.poller.poll(timeout))
        
        #if socket in msgs and msgs[socket] == zmq.POLLIN
        
        if self.presenter_socket in msgs and msgs[self.presenter_socket] == zmq.POLLIN:
            self.process_new_message_from_presenter()
        
        self.controller_interface.process_new_messages()
                
    def process_new_message_from_presenter(self):
        
        router_id, message = self.presenter_socket.recv_multipart()
        message = json.loads(message)
        
        if self.presenter_id not in self.presenter_router_ids:
            self.presenter_router_ids[self.presenter_id] = router_id
        
        message_callback = self.message_callbacks[message['type']]
        message_body = message['body']
        if isinstance(message_body, (tuple, list)):
            message_callback(*message_body)
        else:
            message_callback(message_body)
        
    def handle_add_controller(self, endpoint, controller_id):

        controller = ControllerConnection(self.controller_interface, controller_id)
        self.controllers.append(controller)
        self.controller_interface.register_connection(controller)
        self.controller_interface.connect_to_endpoint(controller_id, endpoint)
        controller.send_message('request_connect', '')

    def handle_remove_controller(self, controller_id):
        
        controller = self.find_controller(controller_id)
    
        controller.close() # close connection in interface
        self.controllers.remove(controller)
        self._send_message_to_presenter('controller_removed', controller_id)

    def handle_forward_to_controller(self, controller_id, controller_message):

        # self.controller_interface.send_forwarded_message(controller_id, controller_message)
        self._send_message_to_controller_by_id(controller_message['type'], controller_message['body'], controller_id)

    def handle_entire_controller_update(self, controller, controller_info):

        self._send_message_to_presenter('entire_controller_update', controller_info)

    def handle_controller_event(self, controller, event_type, event_args):

        self._send_message_to_presenter('controller_event', (controller.id, event_type, event_args))

    def handle_entire_sensor_update(self, controller, sensor_info):
        self._send_message_to_presenter('entire_sensor_update', (controller.id, sensor_info))
    
    def handle_sensor_changed(self, controller, sensor_id, info_name, value):
        '''Propagate change to all presenters.'''
        self._send_message_to_presenter('sensor_changed', (controller.id, sensor_id, info_name, value))
    
    def handle_sensor_removed(self, controller, sensor_id):
        '''Propagate removal to all presenters.'''
        self._send_message_to_presenter('sensor_removed', (controller.id, sensor_id))
    
    def handle_new_sensor_text(self, controller, sensor_id, text):
        
        self._send_message_to_presenter('new_sensor_text', (controller.id, sensor_id, text))
    
    def handle_new_sensor_data(self, controller, sensor_id, utc_time, sys_time, data, data_ok):
        
        self._send_message_to_presenter('new_sensor_data', (controller.id, sensor_id, utc_time, sys_time, data, data_ok))
        
    def handle_error_message(self, controller, message, level):
        ''''''
        self._send_message_to_presenter('error_message', (message, level))
        
    def handle_new_controller_text(self, controller, text):
        
        self._send_message_to_presenter('new_controller_text', (controller.id, text))
        
    def handle_new_source_data(self, controller, sensor_id, source_type, utc_time, sys_time, data):
        
        self._send_message_to_presenter('new_source_data', (controller.id, sensor_id, source_type, utc_time, sys_time, data))
        
    def _send_message_to_presenter(self, message_type, message_body):

        message = {'type': message_type, 'body': message_body}
        
        router_id = self.presenter_router_ids[self.presenter_id]
        self.presenter_socket.send_multipart([router_id, json_dumps_unicode(message)])
        
    def _send_message_to_controller_by_id(self, message_type, message_body, controller_id):

        if controller_id == 'all':  # send to all controllers
            self.controller_interface.send_message_to_all(message_type, message_body)
        else:
            self.controller_interface.send_message(controller_id, message_type, message_body)
        
    def find_controller(self, controller_id):

        for controller in self.controllers:
            if controller.id == controller_id:
                return controller
            
        raise ValueError
        