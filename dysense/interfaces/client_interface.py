# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import zmq
import json

from dysense.interfaces.component_interface import ComponentInterface
from dysense.interfaces.component_connection import ComponentConnection

class ClientInterface(ComponentInterface):
    '''
    Special type of ComponentInterface that acts as a client.
    
    A single instance of this class allows connections to multiple servers using the 
    'wire_to' and 'connect_to' methods. This class maintains a separate ZMQ DEALER (i.e. client)
    socket for each connection in order to address individual servers when sending messages.
    '''
    def __init__(self, context, component_id):
        '''Constructor.  See parent class for arguments.'''

        super(ClientInterface, self).__init__(context, component_id)
        
        # Lookup tables of {server_id: socket} so we can figure out how to address servers.
        # This should only be used to hold valid sockets (i.e. the values should never be None).
        self._server_id_to_socket = {}
        
        self._wired_local_server_info = None
        self._wired_remote_server_info = []
        self._wired_endpoint_info = []
        
    def wire_locally_to(self, server):
        '''Save server info so that when client is setup() it will automatically connect.'''
        
        self._wired_local_server_info = (server.component_id, server.local_endpoint)
       
    def wire_remotely_to(self, server, ip):
        '''Same as wire_locally_to, but allows to connect to a server running in a different process.'''
        
        self._wired_remote_server_info.append((server.component_id, ip, server.ports))

    def wire_to_endpoint(self, server_id, endpoint):
        '''Wire to specified custom endpoint that will automatically connected when interface is setup().'''
        
        self._wired_endpoint_info.append((server_id, endpoint))
        
    def connect_locally_to(self, server):
        '''Connect to server running in same process.  setup() must be called before this method.'''
        
        self.connect_to_endpoint(server.component_id, server.local_endpoint)
      
    def connect_remotely_to(self, server, ip):
        '''Connect to server running in different process.  setup() must be called before this method.'''
        
        # TODO update to try multiple ports
        endpoint = 'tcp://{}:{}'.format(ip, server.ports[0])
        self.connect_to_endpoint(server.component_id, endpoint)
       
    def setup(self):
        '''Try to connect to every server specified using the wire_to_*() methods.'''
       
        if self._wired_local_server_info is not None:
            server_id = self._wired_local_server_info[0]
            endpoint = self._wired_local_server_info[1]
            self._local_server_id = server_id
            self.connect_to_endpoint(server_id, endpoint)
       
        for server_id, ip, ports in self._wired_remote_server_info:
            if len(ports) == 0:
                raise Exception("Can't connect to remote server {} because it doesn't list any ports.".format(server_id))
            # TODO update to try multiple ports
            endpoint = 'tcp://{}:{}'.format(ip, ports[0])
            self.connect_to_endpoint(server_id, endpoint)
            
        for server_id, endpoint in self._wired_endpoint_info:
            self.connect_to_endpoint(server_id, endpoint)
            
    def close_connection(self, component_id):
        
        self._server_id_to_socket.pop(component_id, None)
        
        ComponentInterface.close_connection(self, component_id)
            
    def close(self):
        '''Close the socket used to talk to each server.'''
        
        for _, socket in self._server_id_to_socket.iteritems():
            socket.close()
            
        self._server_id_to_socket = {}
            
    def is_closed(self):
        '''Return true connections to all servers are closed.'''
        
        return len(self._server_id_to_socket) == 0
       
    def connect_to_endpoint(self, server_id, endpoint):
        '''
        Connect client to server with that is bound to the specified endpoint.
        This can be called before the server is bound.
        '''
        if server_id in self._server_id_to_socket:
            # TODO log message that socket to server_id already created.
            existing_socket = self._server_id_to_socket[server_id]
            existing_socket.close()
            self._server_id_to_socket.pop(server_id)
        
        socket = self._context.socket(zmq.DEALER)
        socket.connect(endpoint)
        self._server_id_to_socket[server_id] = socket
        
        # Register socket with pollers
        for poller in self._pollers:
            poller.register(socket, zmq.POLLIN)
        
        try:
            connection = self.lookup_connection(server_id)
        except KeyError:
            # No connection registered yet, so create one automatically.
            connection = ComponentConnection(self, server_id)
            self.register_connection(connection)
 
        # Set the initial state to 'setup' because we're about to send an introduction message.
        connection.update_connection_state('setup')
        
        self._send_introduction_message(server_id)
            
    def _receive_new_message(self):
        '''Return one new message from one of the servers.  If no new messages then raise ZMQError.'''
        for server_id, server_socket in self._server_id_to_socket.iteritems():
            try:
                new_message = json.loads(server_socket.recv(zmq.NOBLOCK))
                return new_message, server_id
            except zmq.ZMQError:
                # Server didn't have a message waiting so try next one.
                pass
                
        # No messages for any server.
        raise zmq.ZMQError
        
    def _send_formatted_message(self, server_id, message):
        '''Send message to the specified server.'''
        
        try:
            socket = self._server_id_to_socket[server_id]
            socket.send(message)
        except KeyError:
            # TODO log some kind of error message
            return # haven't connected to the server yet
