# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import zmq
import json
import time

from dysense.core.utility import json_dumps_unicode
from dysense.interfaces.component_connection import ComponentConnection

class ComponentInterface(object):
    '''
    Generic message interface built on top of ZMQ.
    
    This is an abstract class, and a ClientInterface or ServerInterface should be
    instantiated instead.  In either case it represents a one to many connection.
    Since it's built on top of ZMQ it's inherently asynchronous and can either
    be used for local (same process, different threads) or remote (different process) 
    communication. The remote connections are made over TCP, so they will work for either
    interprocess communication on the same computer, or between different computers.
    
    A simple example is shown below for communication between two threads.
    
    # Thread #1 (main thread)
    context = zmq.Context()
    server = ServerInterface(context, 'example_server, 'c2s')
    server.setup()
    
    client = ClientInterface(context, 'example_client')
    client.wire_locally_to(server)
    <--- pass client object to thread #2 ---->
    
    server.register_callbacks(...) 
    loop:
        server.process_new_messages() # will fire callback when new message is received.
    
    # Thread #2
    client.register_callbacks(...)
    client.setup()  # very important to call setup() in correct thread.
    client.send_message('example_message', example_args...)
    loop:
        client.process_new_messages()
    
    This abstract class is not in charge of the ZMQ sockets, but rather it contains the additional
    functionality such as formatting message, processing new messages, etc.  It also tracks each
    connection that is made through the interface using ComponentConnection objects.  Part of this 
    connection tracking is using a heartbeat message to ensure the other component hasn't crashed.
    '''
    def __init__(self, context, component_id):
        '''
        Constructor.  
        
        :param context: ZMQ context object.  This is threadsafe.
        :param str component_id: unique ID of component (e.g. 'test_server_1')
        '''
        self._context = context
        self.component_id = component_id
        self.heartbeat_period = 2 # (seconds) how quickly heartbeat messages should be sent out.
        
        # Dictionary holding user-defined callbacks for when a certain type of message is received.
        self._message_type_to_callback = {}
        
        # Associate connected component ID with it's corresponding ComponetConnection object.
        self._component_id_to_connection = {}
        
        # List of pollers that new sockets will automatically be registered with.
        self._pollers = []
        
    def register_callbacks(self, callbacks):
        '''Register each item {message_type: callback} in specified dictionary.'''
        
        for message_type, callback in callbacks.iteritems():
            self.register_callback(message_type, callback)

    def register_callback(self, message_type, callback):
        '''Register callback method to be called when the specified message type is received.'''
        
        self._message_type_to_callback[message_type] = callback
        
    def register_connection(self, connection):
        '''
        Register the connection object for a component that is expected to connect.  This is 
        useful for custom connection objects which track additional information.
        '''
        self._component_id_to_connection[connection.id] = connection
        
    def register_poller(self, poller):
        
        self._pollers.append(poller)
        
    def close_connection(self, component_id):
        
        self._component_id_to_connection.pop(component_id, None)
        
    def lookup_connection(self, component_id):
        
        return self._component_id_to_connection[component_id]

    def process_new_messages(self):
        '''Receive all buffered messages and call their associated callback.'''
        
        while True:
            try:
                message, sender_id = self._receive_new_message()
                self._process_new_message(message, sender_id)
            except zmq.ZMQError:
                break # no more messages
            
        self._refresh_connection_states()
                        
    def send_message(self, recipient_id, message_type, message_body):
        '''
        Send message to the component with the specified recipient_id.
        
        message_body can be any JSON serializable type, but it much match the type of 
        arguments that are expected for the specified message_type.  
        
        Example:  interface.send_message('sensor123', 'command_message', 'some_command')  
        '''
        message = {'type': message_type, 'body': message_body}

        try:
            json_message = json_dumps_unicode(message)
            self._send_formatted_message(recipient_id, json_message)
        except AttributeError:
            pass # socket isn't created so can't send message

    def send_message_to_all(self, message_type, message_body):
        '''Send message to every connected component.'''

        for component_id in self._component_id_to_connection.keys():
            self.send_message(component_id, message_type, message_body)
            
    def _refresh_connection_states(self):
        '''Update the state (e.g. timed-out, opened, etc) of each connection.'''
        
        for connection in self._component_id_to_connection.values():
            connection.refresh_state()
            
    def _process_new_message(self, message, sender_id):
        '''
        Invoke the callback corresponding to the new message. If the callback arguments are
        a list or tuple then they'll automatically be expanded when calling the callback.
        '''
        is_introduction_message = message['type'] == 'introduction'

        if is_introduction_message:
            # Standard callback to create a new component connection.
            self._handle_introduction_message(message, sender_id)

        try:
            # Lookup connection for component that sent message.
            component = self._component_id_to_connection[sender_id]
        except KeyError:
            return # component doesn't exist, it was likely recently removed.
        
        try:
            message_callback = self._message_type_to_callback[message['type']]
        except KeyError:
            if is_introduction_message or message['type'] == 'heartbeat':
                # Introduction messages are optional for user to handle and so are
                # heartbeats.  Nothing special needs to be done when receiving heartbeats
                # since every received messages is essentially treated like a heartbeat.
                message_callback = None
            else:    
                raise Exception("No callback registered for message type '{}'".format(message['type']))
        
        if message_callback is not None:
            message_body = message['body']
            if isinstance(message_body, (tuple, list)):
                # Expand arguments for convenience.
                message_callback(component, *message_body)
            else:
                message_callback(component, message_body)
            
        component.update_for_new_message()
        
    def _send_introduction_message(self, recipient_id):
        '''This is the first message that must be sent when connecting to a new component.'''
        
        if self.heartbeat_period is None:
            raise Exception("Setup error: Heartbeat period not set.")
       
        message_body = {'sender_id': self.component_id, 'heartbeat_period': self.heartbeat_period}
        
        self.send_message(recipient_id, 'introduction', message_body)
        
    def _handle_introduction_message(self, message, sender_id):
        '''
        Handle new component connection.  If a connection object hasn't been registered for the 
        new component_id, then a new generic one will be created automatically.
        '''     
        # The rate at which the sending component will send heartbeat messages.
        heartbeat_period = float(message['body']['heartbeat_period'])
        
        # The sender_id that is specified in the message may be different.  
        _ = message['body']['sender_id']
        
        try: 
            connection = self._component_id_to_connection[sender_id]
        except KeyError:
            # No connection object has been registered for this ID so create a generic one.
            # The connection will register itself.
            connection = ComponentConnection(self, sender_id)
            
        connection.update_heartbeat_period(heartbeat_period) 
        
        self._post_introduction_hook(message)
        
    def _post_introduction_hook(self, message):
        '''Subclass can override to execute code after introduction message is received.'''
        return
