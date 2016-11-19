# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import zmq
import json
import time

class ComponentConnection(object):
    '''
    Represent the connection between a client and a server interface and
    tracks information such as the current state of the connection as well
    as manages all of the heartbeating.
    
    If a client interface is connected to a server, then the client will have
    a ComponentConnection object, and the server will also have it's own 
    ComponentConnection for the client.
    '''
    # The keys are the possible states the connection can be in.
    # The values are the 'health' associated with each state.
    possible_states = {'closed': 'neutral',
                       'setup': 'neutral',
                       'opened': 'good',
                       'timed_out': 'bad',
                       'error': 'bad',
                       }
    
    def __init__(self, interface, connected_component_id):
        '''
        Constructor.
        
        :param interface: ServerInterface or ClientInterface that owns this connection object.
        :param str connected_component_id: Unique ID of component on other end of connection.
        '''
        self._interface = interface
        
        self._connected_component_id = connected_component_id
        
        self._connection_state = 'closed'
        self._connection_health = ComponentConnection.possible_states[self._connection_state]

        # Set to true when the connected component reports that it's closing down.
        self._closing = False
        
        # Set to a default value that can be overridden later.
        self.update_heartbeat_period(2)
        
        # How long to wait for component to send first message before timing out. (in seconds)
        self._max_time_to_receive_message = self._component_timeout_thresh * 1.5
        
        # Last system time that we tried to process new messages from component.
        self._last_message_processing_time = 0
        
        # Last system time that we received a new message from component.
        self._last_received_message_time = 0
        
        # Last time we sent out a heartbeat message.
        self._last_sent_heartbeat_time = 0
        
        # Time that interface was connected to component.
        self._connection_setup_time = 0
    
        # How many message have been received from component.
        self._num_messages_received = 0
        
        # Register with interface.
        self._interface.register_connection(self)
        
    @property
    def connection_state(self):
        return self._connection_state
        
    @property
    def num_messages_received(self):
        return self._num_messages_received
        
    @property
    def id(self):
        return self._connected_component_id
        
    def update_heartbeat_period(self, new_value):
        
        # How often (in seconds) we should receive a new message from component.
        self._connected_component_heartbeat_period = new_value
        
        # If we don't receive a new message in this time then consider component dead. (in seconds) 
        self._component_timeout_thresh = self._connected_component_heartbeat_period * 10
        
    def send_message(self, message_type, message_body):
        '''Client ID is recipient'''
        
        self._interface.send_message(self._connected_component_id, message_type, message_body)
        
    def reset(self):
        '''Reset all fields and register component.'''
        
        self.update_connection_state('closed')
        self._closing = False
        self._last_message_processing_time = 0
        self._last_received_message_time = 0
        self._last_sent_heartbeat_time = 0
        self._connection_setup_time = 0
        self._num_messages_received = 0
        
        # Make sure component is registered in case in was removed when closed.
        self._interface.register_connection(self)
        
    def close(self):
        '''
        Should be called when the connected component notifies that it's closing.
        This method will close the connection which will not allow any future messages to be sent/received.
        '''
        self._closing = True
        self.update_connection_state('closed')
        self._interface.close_connection(self._connected_component_id)
        
    def refresh_state(self):
        '''
        Update connection state based on when messages have been received.
        This will be called automatically be interface after processing new messages.
        '''
        # Mark that we've tried to receive message from component.
        self._last_message_processing_time = time.time()

        if self.stopped_responding() and not self._closing:
            self.update_connection_state('timed_out')
        else:
            if self.need_to_send_heartbeat():
                self.send_heartbeat()
                
            if (self._connection_state != 'opened') and self._num_messages_received > 0 and not self._closing:
                # Just started receiving messages.
                self.update_connection_state('opened')
        
    def update_connection_state(self, new_value):
        '''Update the connection state and health, and notify that the state changed.'''
        
        if self._connection_state == new_value:
            return
        
        if new_value == 'setup':
            # Save when connection is setup to detect if component never responds at all.
            self._connection_setup_time = time.time()
        
        self._connection_state = new_value
        self._connection_health = ComponentConnection.possible_states[new_value]
        
        self.connection_state_changed(self._connection_state)
        
    def update_for_new_message(self):
        '''Update time tracking fields for when a new message is received.'''
        
        self._last_received_message_time = time.time()
        self._num_messages_received += 1
        
    def connection_state_changed(self, new_state):
        '''Subclass can override to be notified when state changes.'''
    
        return 
        
    def send_heartbeat(self):
        '''Send heartbeat message to client.'''
        
        self.send_message('heartbeat', '')
        self._last_sent_heartbeat_time = time.time()
        
    def stopped_responding(self):
        '''Return true if it's been too long since we've received a new message from the component.'''
        
        if self._connection_state in ['closed']:
            return False # Shouldn't be receiving messages.
        
        if self._connection_setup_time == 0 or self._last_message_processing_time == 0:
            # Haven't tried to receive any messages yet so can't know if we're timed out.
            return False 
        
        if self._num_messages_received == 0:
            # Give component more time to send first message.
            time_since_connecting = self._last_message_processing_time - self._connection_setup_time
            return time_since_connecting > self._max_time_to_receive_message
            
        # We're getting messages so use normal timeout.
        time_since_last_message = self._last_message_processing_time - self._last_received_message_time
        return time_since_last_message > self._component_timeout_thresh
            
    def need_to_send_heartbeat(self):
        '''Return true if it's time to send a heartbeat message to component.'''
        
        time_since_last_heartbeat = time.time() - self._last_sent_heartbeat_time 
        return time_since_last_heartbeat > self._interface.heartbeat_period