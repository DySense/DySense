# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import zmq
import json

from dysense.interfaces.component_interface import ComponentInterface

class ServerInterface(ComponentInterface):
    '''
    Special type of ComponentInterface that acts as a server.

    A single instance of this class can support connections to multiple clients using a
    ZMQ ROUTER (i.e. server) socket.  These clients can connect using the local (same process)
    endpoint, or optionally the socket can also be bound to a remote port to communicate over TCP.
    '''
    def __init__(self, context, component_id, local_name, version, ports=None, all_addresses=True):
        '''
        Constructor.

        :param str local_name: name of the local endpoint for the server to bind to.
        :param list ports: port numbers to try to connect to for TCP communcation.  Will only bind
                          to the first one that isn't already occupied.
        :param bool all_addresses: If true then will bind remote port to all network addresses (0.0.0.0)
                                   rather than just the home address (127.0.0.1)
        '''
        super(ServerInterface, self).__init__(context, component_id, version)

        self.local_endpoint = 'inproc://' + local_name

        if ports is None:
            ports = []
        self.ports = ports

        ip = '0.0.0.0' if all_addresses else '127.0.0.1'
        self._remote_endpoints = ['tcp://{}:{}'.format(ip, port) for port in ports]

        self.remote_endpoint = None

        # Lookup tables of {client_id: router_id} so we can figure out how to address clients.
        self._client_id_to_router_id = {}
        # Reverse lookup to determine who sent new message.
        self._router_id_to_client_id = {}

        self._socket = None

    def setup(self):
        '''Setup the socket and bind to the default endpoints.'''

        self._socket = self._context.socket(zmq.ROUTER)

        for poller in self._pollers:
            poller.register(self._socket, zmq.POLLIN)

        self.bind_to_endpoint(self.local_endpoint)
        if len(self._remote_endpoints) > 0:
            self.remote_endpoint = self._bind_to_first_open_endpoint()

    def close_connection(self, component_id):

        self._client_id_to_router_id.pop(component_id, None)

        ComponentInterface.close_connection(self, component_id)

    def close(self):
        '''Close the socket if it's open.'''

        if self._socket:
            self._socket.close()
            self._socket = None

    def is_closed(self):
        '''Return true if the socket is closed.'''

        return self._socket is None

    def bind_to_endpoint(self, endpoint):
        '''Bind the server socket to the specified endpoint.'''

        self._socket.bind(endpoint)

    def _receive_new_message(self):
        '''
        Return next waiting message if available, otherwise raise ZMQError

        If message isn't an introduction message and no router ID exists for it,
        for example the connection just closed down, then a client_id of '_n/a' will be returned.
        '''

        router_id, message = self._socket.recv_multipart(zmq.NOBLOCK)
        message = json.loads(message)

        if message['type'] == 'introduction':
            client_id = message['body']['sender_id']
            self._client_id_to_router_id[client_id] = router_id
            self._router_id_to_client_id[router_id] = client_id
        else:
            try:
                client_id = self._router_id_to_client_id[router_id]
            except KeyError:
                client_id = '_n/a' # don't have a connection for this message

        return message, client_id

    def _send_formatted_message(self, client_id, message):
        '''Send the already formatted message to specified client.'''

        try:
            router_id = self._client_id_to_router_id[client_id]
            self._socket.send_multipart([router_id, message], zmq.NOBLOCK)
        except KeyError:
            return  # haven't received message from component yet so don't know how to address it.
        except zmq.ZMQError:
            return # can't send message

    def _bind_to_first_open_endpoint(self):
        '''Connect to the first remote endpoint that's not already occupied. Raise Exception if cannot bind to any.'''

        for endpoint in self._remote_endpoints:
            try:
                self._socket.bind(endpoint)
                return endpoint
            except (zmq.ZMQBindError, zmq.ZMQError):
                continue  # Try next endpoint

        raise Exception("Failed to bind to any of the following endpoints {}".format(endpoints))

    def _post_introduction_hook(self, message):
        '''Automatically return introduction message after handling new introduction message.'''

        self._send_introduction_message(message['body']['sender_id'])
