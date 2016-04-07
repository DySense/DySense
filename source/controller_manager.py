#!/usr/bin/env python

import time
import zmq
import threading
import json

class ControllerConnection(object):
    
    def __init__(self, socket, controller_name='N/A', controller_id=None):

        self.name = controller_name
        self.id = controller_id
        self.socket = socket
        
    @property
    def public_info(self):
        return { 'name': self.name,
                 'id': self.id }
        
    def stopped_responding(self):
        return False

class ControllerManager(object):
    
    def __init__(self, context):
        
        self.context = context
        
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
                                  'entire_sensor_update': self.handle_entire_sensor_update,
                                  'sensor_changed': self.handle_sensor_changed,
                                  'sensor_removed': self.handle_sensor_removed,
                                  'new_sensor_text': self.handle_new_sensor_text,
                                  'new_sensor_data': self.handle_new_sensor_data,
                                  'new_time': self.handle_new_time,
                                  'error_message': self.handle_error_message,
                                  'new_controller_text': self.handle_new_controller_text,
                                  }

    def run(self):

        try:
            self.run_message_loop()
        finally:
            self.close_down()
    
    def close_down(self):
        
        for controller in self.controllers:
            controller.socket.close()
            
        if self.presenter_socket:
            self.presenter_socket.close()
    
    def run_message_loop(self):
        
        self.presenter_socket = self.context.socket(zmq.ROUTER)
        self.presenter_socket.bind(self.presenter_local_endpoint)
        
        # Use a poller so we can use timeout to check if any controllers aren't responding.
        self.timeout = 1000  # milliseconds
        self.poller = zmq.Poller()
        self.poller.register(self.presenter_socket, zmq.POLLIN)
    
        while True:
            
            if self.stop_request.is_set():
                break  # from main loop
            
            self.process_new_messages()

            for controller in self.controllers:
                if controller.stopped_responding():
                    # TODO Notify UI and close down controller.
                    pass
            
    def process_new_messages(self):
        
        msgs = dict(self.poller.poll(self.timeout)) 
        
        if self.presenter_socket in msgs and msgs[self.presenter_socket] == zmq.POLLIN:
            # New message is waiting.
            self.process_new_message_from_presenter()
            
        for controller in self.controllers:
            if controller.socket in msgs and msgs[controller.socket] == zmq.POLLIN:
                # New message is waiting.
                self.process_new_message_from_controller(controller)
                
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
        
    def process_new_message_from_controller(self, controller):
        
        message = json.loads(controller.socket.recv())
        controller.id = message['id']
        message_body = message['body']
        
        message_callback = self.message_callbacks[message['type']]
        
        if isinstance(message_body, (tuple, list)):
            message_callback(controller, *message_body)
        else:
            message_callback(controller, message_body)
        
    def handle_add_controller(self, endpoint, controller_name):

        socket = self.context.socket(zmq.DEALER)
        socket.connect(endpoint)
        controller = ControllerConnection(socket, controller_name)
        self.controllers.append(controller)
        self.poller.register(socket, zmq.POLLIN)
        self._send_message_to_controller('request_connect', '', controller)

    def handle_remove_controller(self, controller_id):
        
        controller = self.find_controller(controller_id)
    
        controller.sock.close()
        self.controllers.remove(controller)
        self._send_message_to_presenter('controller_removed', controller_id)

    def handle_forward_to_controller(self, controller_id, controller_message):

        self._send_message_to_controller_by_id(controller_message['type'], controller_message['body'], controller_id)

    def handle_entire_controller_update(self, controller, controller_info):

        self._send_message_to_presenter('entire_controller_update', controller_info)

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
    
    def handle_new_sensor_data(self, controller, sensor_id, data, data_ok):
        
        self._send_message_to_presenter('new_sensor_data', (controller.id, sensor_id, data, data_ok))
    
    def handle_new_time(self, controller, time):
        '''Could come from any controller.'''
        utc_time, sys_time = time
        if sys_time <= 0:
            # Time came from another computer so need to record time.
            sys_time = time.time()
        self._send_message_to_controller('new_time', (utc_time, sys_time), local_controller)
        
    def handle_error_message(self, controller, message, level):
        ''''''
        self._send_message_to_presenter('error_message', (message, level))
        
    def handle_new_controller_text(self, controller, text):
        
        self._send_message_to_presenter('new_controller_text', (controller.id, text))
        
    def _send_message_to_presenter(self, message_type, message_body):

        message = {'type': message_type, 'body': message_body}
        
        router_id = self.presenter_router_ids[self.presenter_id]
        self.presenter_socket.send_multipart([router_id, json.dumps(message)])
        
    def _send_message_to_controller_by_id(self, message_type, message_body, controller_id):

        message = {'type': message_type, 'body': message_body}

        if controller_id == 'all':  # send to all controllers
            for controller in self.controllers:
                controller.socket.send(json.dumps(message))
        else:  # just send to single controller
            controller = self.find_controller(controller_id)
            controller.socket.send(json.dumps(message))
            
    def _send_message_to_controller(self, message_type, message_body, controller):

        message = {'type': message_type, 'body': message_body}
        controller.socket.send(json.dumps(message))
        
    def find_controller(self, controller_id):
    
        for controller in self.controllers:
            if controller.id == controller_id:
                return controller
            
        raise ValueError
        
