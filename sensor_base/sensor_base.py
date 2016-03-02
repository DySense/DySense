#!/usr/bin/env python

import time
import zmq
import json

class SensorBase(object):
    '''
    Base class for all sensor drivers.
    
    All sensor drivers written in python should inherit from this class. Most of its public interface
    is over sockets where inputs are time/commands and outputs are data/messages/status. The only
    public method is run() which handles everything.
    '''
    
    # The keys are the possible states the driver can be in.
    # The values are the 'health' associated with each state.
    possible_states = {'closed': 'neutral',
                       'waiting_for_time': 'neutral',
                       'normal': 'good',
                       'timed_out': 'bad',
                       'error': 'bad',
                       }

    def __init__(self, sensor_id, context, connect_endpoint, min_loop_period=0.25, max_closing_time=0, 
                 heartbeat_period=0.5, wait_for_valid_time=True):
        '''
        Base constructor.
        
        Args:
            connect_endpoint - controller endpoint to connect to and get messages from.
            min_loop_period - minimum duration (in seconds) that data collection loop will run.
            max_closing_time - maximum number of seconds sensor needs to wrap up before being force closed.
            heartbeat_period - How often (in seconds) we should receive a new message from client and
                                 how often we should send one back.
        '''
        self.sensor_id = str(sensor_id)
        self.context = context
        self.connect_endpoint = connect_endpoint
        self.min_loop_period = max(0, min_loop_period)
        self.max_closing_time = max(0, max_closing_time)
        self.heartbeat_period = max(0.1, heartbeat_period)
        self.wait_for_valid_time = wait_for_valid_time
        
        # Set to true when receive 'close' command from client.
        self.received_close_request = False
        
        # Current sensor state. Private to keep in ensure client is notified when one changes.
        self._state = 'closed'
        self.health = SensorBase.possible_states[self._state]
        
        # True if sensor shouldn't be saving/sending any data.
        self._paused = True

        # Time references used to improve precision when sensor requests current time.
        self._last_received_sys_time = 0
        self._last_received_utc_time = 0
        
        # Associate callback methods with different message types.
        self.message_table = { 'command': self.handle_command, 
                               'time': self.handle_new_time,
                               'heartbeat': self.handle_new_heartbeat }
        
        # ZMQ socket for communicating with sensor controller.
        self.socket = None
        
        # The time that the current run() loop started at. Used for throttling how fast the main loop runs.
        self.run_loop_start_time = 0;
        
        # If we don't receive a new message in this time then consider client dead. (in seconds) 
        self.client_timeout_thresh = self.heartbeat_period * 10
        
        # How long to wait for client to send first message before timing out. (in seconds)
        self.max_time_to_receive_message = self.client_timeout_thresh * 1.5
        
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
        
        # How many message 'data' messages have been sent to client.
        self.num_data_messages_sent = 0
        
    @property
    def time(self):
        '''Return current UTC time or 0 if haven't received a time yet.'''
        utc_time = self._last_received_utc_time
        if utc_time > 0:
            # Account for time that has elapsed since last time we received a time message.
            elapsed_time = time.time() - self._last_received_sys_time
            if elapsed_time > 0:
                utc_time += elapsed_time
                
        return utc_time
    
    @property
    def state(self):
        '''Return the current sensor state.'''
        return self._state
    
    @state.setter
    def state(self, new_state):
        '''Update state + status and notify client that they changed.'''
        if new_state not in SensorBase.possible_states:
            raise ValueError("Invalid sensor state {}".format(new_state))
        if new_state == self._state:
            return # don't keep sending out new status updates
        self._state = new_state
        self.health = SensorBase.possible_states[new_state]
        self.send_status_update()
        
    @property
    def paused(self):
        '''Return true if the sensor is currently paused.'''
        return self._paused
    
    @paused.setter
    def paused(self, new_value):
        '''Set paused to true/false and then notify client that the status changed if it's different.'''
        if new_value == self._paused:
            return # don't keep sending out new status updates
        self._paused = new_value
        self.send_status_update()

    def run(self):
        '''Set everything up, collect data and then close everything down when finished.'''
        try:
            self.setup_interface()
            self.setup()
    
            while True:
                
                # Save off time so we can limit how fast loop runs.
                self.run_loop_start_time = time.time()
                
                # Handle any messages received over receive socket.
                self.process_new_messages()

                if self.client_timed_out():
                    raise Exception("Controller connection timed out.") 
                
                if self.received_close_request:
                    self.send_text('Closing...')
                    break # end main loop

                if self.need_to_send_heartbeat():
                    self.send_message('new_sensor_heartbeat', ' ')
                    self.last_sent_heartbeat_time = time.time()
     
                # Give sensor a chance to read in new data.  This either needs to block until next read
                # or call wait_for_next_loop().
                reported_state = self.read_new_data()
                
                # If sensor is ok then override state if we're still waiting for a valid time.
                reported_bad_state = SensorBase.possible_states[reported_state] == 'bad'
                waiting_for_time = self.wait_for_valid_time and self.time == 0
                if not reported_bad_state and waiting_for_time:
                    reported_state = 'waiting_for_time'
                    
                self.state = reported_state
                
        except Exception as e:
            self.state = 'error'
            self.send_text("{}".format(repr(e)))
        finally:
            if self.health != 'bad':
                # The closed state is only for when things closed down on request... not because an error occured.
                self.state = 'closed'
            self.received_close_request = False
            self.send_event('closing')
            self.pause()
            self.close()
            self.close_interface()
        
    def close(self):
        '''Stop reading sensor data and close down any resources. Sensor must override.'''
        raise NotImplementedError
    
    def is_closed(self):
        '''Return true if sensor is closed.'''
        raise NotImplementedError
    
    def read_new_data(self):
        '''Try to read in new data from sensor.  Only called when not paused.  Sensor must override.'''
        raise NotImplementedError
   
    def setup(self):
        '''Called before collection loop starts. Driver can override to make connection to sensor.'''
        return
   
    def pause(self):
        '''Called when pause command is received or sensor closes. Driver can override to notify sensor.'''
        return
    
    def resume(self):
        '''Called when resume command is received. Driver can override to notify sensor.'''
        return
    
    def handle_special_command(self, command):
        '''Override to handle sensor specified commands (e.g. trigger)'''
        return
        
    def setup_interface(self):
        '''Set up client socket and then send status update to controller.'''
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.connect(self.connect_endpoint)

        self.send_status_update()
        
        self.interface_connection_time = time.time()
        
    def close_interface(self):
        '''Close down socket.'''
        if self.socket:
            self.socket.close()
        
    def send_status_update(self):
        '''
        Notify client of status change (status = state + health + paused)
        This is called automatically when class fields change.
        '''
        self.send_message('new_sensor_status', (self.state, self.health, self.paused))
        
    def handle_data(self, data):
        '''Send data to client if not paused.'''
        if not self.should_record_data():
            return
        # Make sure data is sent as a tuple.
        self.send_message('new_sensor_data', (data,))
        self.num_data_messages_sent += 1
        
    def should_record_data(self):
        '''Return true if the sensor is in a state where it should be trying to record data.'''
        still_need_time_reference = self.wait_for_valid_time and self.time == 0
        return not (still_need_time_reference or self.paused)
    
    def wait_for_next_loop(self):
        '''
        Can optionally be called at the end of read_new_data() to limit how fast main loop runs.
        This uses the min_loop_period attribute to determine how long to wait.  If the amount of
        time has already exceed min_loop_period then this method will return right away.
        '''
        loop_duration = time.time() - self.run_loop_start_time
        if loop_duration < self.min_loop_period:
            time_to_sleep = self.min_loop_period - loop_duration
            time.sleep(max(0, time_to_sleep))

    def send_text(self, text):
        '''Send text message to client (like print)'''
        self.send_message('new_sensor_text', text)
        
    def send_event(self, event_name):
        '''Send event to notify client something important happened.'''
        self.send_message('new_sensor_event', event_name)

    def send_message(self, message_type, message_body):
        '''
        Send message to client in JSON format.
        
        Args:
            message_type - provide context of message being sent (e.g. 'text')
            message_body - tuple or simple type.  All elements must be JSON serializable.
        '''
        try:
            self.socket.send(json.dumps({'sensor_id': self.sensor_id,
                                         'type': message_type,
                                         'body': message_body}))
        except AttributeError:
            pass # socket isn't created so can't send message
    
    def process_new_messages(self):
        '''Receive and process all messages in socket queue.'''
        while True:
            
            try:
                message = json.loads(self.socket.recv(zmq.NOBLOCK))
            except zmq.ZMQError:
                break # no more messages

            message_callback = self.message_table[message['type']]
            message_callback(message['body'])
            
            self.num_messages_received += 1
            self.last_received_message_time = time.time()
            
        self.last_message_processing_time = time.time()

    def handle_command(self, command):
        '''
        Deal with a new command (e.g. 'close') received from client.
        
        If the command isn't a generic one then it will be passed to handle_special_command.
        '''
        if command == 'close':
            self.received_close_request = True
        elif command == 'pause':
            self.paused = True
            self.pause()
        elif command == 'resume':
            self.paused = False
            self.resume()
        else:
            self.handle_special_command(command)
            
    def handle_new_time(self, times):
        '''
        Process new time reference received from client.
        
        Correct for any time that has elapsed since utc_time was last updated.
        Save this time off so we can use it to calculate a more precise timestamp later.
        
        Args:
            times - tuple of (utc_time, sys_time) where sys_time is the system time from time.time()
                    when utc_time was last updated.
        '''
        utc_time, sys_time = times
        
        self._last_received_sys_time = time.time()
        corrected_utc_time = utc_time + (self._last_received_sys_time - sys_time)
        self._last_received_utc_time = corrected_utc_time
            
    def handle_new_heartbeat(self, unused):
        # Don't need to do anything since all messages are treated as heartbeats.
        pass
            
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
        return time_since_last_heartbeat > self.heartbeat_period
