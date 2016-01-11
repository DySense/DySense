#!/usr/bin/env python

import time

class TimeoutWatcher:
    '''''' 
    
    def __init__(self, heartbeat_duration=0.5, timeout_multiplier=5, max_time_to_receive_message=10):
        '''
        Constructor
        
        Args:
            heartbeat_duration - How often (in seconds) we should receive a new message from client and
                                 how often we should send one back.
            timeout_multiplier - how much to multiply heartbeat_duration by to use as a threshold for 
                                 determining when client has timed out. 
            max_time_to_receive_message - how long to wait for client to send first message before timing out.
        '''
        
        self.heartbeat_duration = heartbeat_duration
        self.max_time_to_receive_message = max_time_to_receive_message
        
        # If we don't receive a new message in this time then consider client dead. (in seconds) 
        self.client_timeout_thresh = self.heartbeat_duration * timeout_multiplier
        
        # Last system time that we tried to process new messages from client.
        self.last_message_processing_time = 0
        
        # Last system time that we received a new message from client.
        self.last_received_message_time = 0
        
        # Last time sensor sent out heartbeat message.
        self.last_sent_heartbeat_time = 0
        
        # Time that interface was connected to client.
        self.interface_connection_time = 0
    
        # How many message have been received from client.
        self.num_messages_received = 0
        
    def client_timed_out(self):
        '''Return true if it's been too long since we've received a new message from client.'''
        if self.interface_connection_time == 0 or self.last_message_processing_time == 0:
            # Haven't tried to receive any messages yet so can't know if we're timed out.
            return False 
        
        if self.num_messages_received == 0:
            # Give client more time to send first message.
            time_since_connecting = self.last_message_processing_time - self.interface_connection_time
            return time_since_connecting > self.max_time_to_receive_message
            
        # We're getting messages so use normal timeout.
        time_since_last_message = self.last_message_processing_time - self.last_received_message_time
        return time_since_last_message > self.client_timeout_thresh
            
    def need_to_send_heartbeat(self):
        '''Return true if it's time to send a heartbeat message to client.'''
        time_since_last_heartbeat = time.time() - self.last_sent_heartbeat_time 
        return time_since_last_heartbeat > self.heartbeat_duration