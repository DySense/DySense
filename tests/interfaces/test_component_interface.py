# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

import zmq
import time

from dysense.interfaces.server_interface import ServerInterface
from dysense.interfaces.client_interface import ClientInterface

class TestLocalConnection(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.num_messages_client_received = 0
        self.num_messages_server_received = 0
        
        self.num_introduction_message_client_received = 0
        self.num_introduction_message_server_received = 0

    def test_normal_message(self):
        
        context = zmq.Context()
        
        server_id = 'test_server_1'
        client_id = 'test_client_1'
        
        # TODO do we need to specify what type of client?
        server = ServerInterface(context, server_id, 'c2s')
        client = ClientInterface(context, client_id)
        
        server.heartbeat_period = 3
    
        client.wire_locally_to(server)
        #client.wire_remotely_to(server, '192.1.1.1')
    
        server.register_callback('introduction', self.callback_server_introduction)
        server.register_callback('server_test_message', self.callback_server_test_message)
    
        client.register_callback('introduction', self.callback_client_introduction)
        client.register_callback('client_test_message', self.callback_client_test_message)
    
        # Will setup socket and send introduction messages since already wired together.
        server.setup()
        client.setup()

        # Server should have received introduction message 
        server.process_new_messages()
        self.assertEqual(self.num_introduction_message_server_received, 1)
        
        # Client now should have received return introduction message 
        client.process_new_messages()
        self.assertEqual(self.num_introduction_message_client_received, 1)
        
        # TODO verify connection states
        
        # Test that client can send message to server
        client.send_message(server_id, 'server_test_message', 'arg1')
        server.process_new_messages()
        self.assertEqual(self.num_messages_server_received, 1)
        
        # Test that server can send message back to client
        server.send_message(client_id, 'client_test_message', ('arg1', 'arg2'))
        client.process_new_messages()
        self.assertEqual(self.num_messages_client_received, 1)
        
        # When client receives first message it will auto reply using the connection
        # object passed to the callback.  Make sure server got this reply.
        server.process_new_messages()
        self.assertEqual(self.num_messages_server_received, 2)
        
        server.close()
        client.close()
        
    def callback_server_introduction(self, connection, arguments):
        self.num_introduction_message_server_received += 1
        
    def callback_client_introduction(self, connection, arguments):
        self.num_introduction_message_client_received += 1
        
    def callback_server_test_message(self, connection, arg1):
        self.num_messages_server_received += 1
    
    def callback_client_test_message(self, connection, arg1, arg2):
        self.num_messages_client_received += 1
        if self.num_introduction_message_client_received == 1:
            # Auto reply to server to test using connection object
            connection.send_message('server_test_message', 'arg1')
        
class TestRemoteConnection(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.num_messages_client_received = 0
        self.num_messages_server_received = 0
        
        self.num_introduction_message_client_received = 0
        self.num_introduction_message_server_received = 0

    def test_normal_message(self):
        
        context = zmq.Context()
        
        server_id = 'test_server_1'
        client_id = 'test_client_1'
        
        server = ServerInterface(context, server_id, 'c2s', [61110], all_addresses=False)
        client = ClientInterface(context, client_id)

        client.wire_remotely_to(server, '127.0.0.1')
    
        server.register_callback('introduction', self.callback_server_introduction)
        server.register_callback('server_test_message', self.callback_server_test_message)
    
        client.register_callback('introduction', self.callback_client_introduction)
        client.register_callback('client_test_message', self.callback_client_test_message)
    
        # Will setup socket and send introduction messages since already wired together.
        server.setup()
        client.setup()
    
        # Server should have received introduction message 
        time.sleep(0.25)
        server.process_new_messages()
        self.assertEqual(self.num_introduction_message_server_received, 1)
        
        # Client now should have received return introduction message 
        time.sleep(0.25)
        client.process_new_messages()
        self.assertEqual(self.num_introduction_message_client_received, 1)
        
        # Test that client can send message to server
        client.send_message(server_id, 'server_test_message', 'arg1')
        time.sleep(0.25)
        server.process_new_messages()
        self.assertEqual(self.num_messages_server_received, 1)
        
        # Test that server can send message back to client
        server.send_message(client_id, 'client_test_message', ('arg1', 'arg2'))
        time.sleep(0.25)
        client.process_new_messages()
        self.assertEqual(self.num_messages_client_received, 1)
        
        # When client receives first message it will auto reply using the connection
        # object passed to the callback.  Make sure server got this reply.
        time.sleep(0.25)
        server.process_new_messages()
        self.assertEqual(self.num_messages_server_received, 2)
    
        server.close()
        client.close()
        
    def callback_server_introduction(self, connection, arguments):
        self.num_introduction_message_server_received += 1
        
    def callback_client_introduction(self, connection, arguments):
        self.num_introduction_message_client_received += 1
        
    def callback_server_test_message(self, connection, arg1):
        self.num_messages_server_received += 1
    
    def callback_client_test_message(self, connection, arg1, arg2):
        self.num_messages_client_received += 1
        if self.num_introduction_message_client_received == 1:
            # Auto reply to server to test using connection object
            connection.send_message('server_test_message', 'arg1')

class TestMultiClientConnection(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.num_messages_client1_received = 0
        self.num_messages_client2_received = 0
        self.num_messages_server_received = 0

    def test_normal_message(self):
        
        context = zmq.Context()
        
        server_id = 'test_server_1'
        client1_id = 'test_client_1'
        client2_id = 'test_client_2'
        
        # TODO do we need to specify what type of client?
        server = ServerInterface(context, server_id, 'c2s')
        client1 = ClientInterface(context, client1_id)
        client2 = ClientInterface(context, client2_id)

        # Connect second client after first setup.
        client1.wire_locally_to(server)

        server.register_callback('server_test_message', self.callback_server_test_message)
        client1.register_callback('client_test_message', self.callback_client1_test_message)
        client2.register_callback('client_test_message', self.callback_client2_test_message)
    
        server.setup()
        client1.setup()

        # Test post-setup connect.
        client2.connect_locally_to(server)

        # Test that clients can send message to server
        client1.send_message(server_id, 'server_test_message', 'arg1')
        client2.send_message(server_id, 'server_test_message', 'arg1')
        server.process_new_messages()
        self.assertEqual(self.num_messages_server_received, 2)
        
        # Test that server can send message back to all clients
        server.send_message_to_all('client_test_message', ('arg1', 'arg2'))
        client1.process_new_messages()
        client2.process_new_messages()
        self.assertEqual(self.num_messages_client1_received, 1)
        self.assertEqual(self.num_messages_client2_received, 1)
        
        server.close()
        client1.close()
        client2.close()
        
    def callback_server_test_message(self, connection, arg1):
        self.num_messages_server_received += 1
    
    def callback_client1_test_message(self, connection, arg1, arg2):
        self.num_messages_client1_received += 1

    def callback_client2_test_message(self, connection, arg1, arg2):
        self.num_messages_client2_received += 1
        
class TestMultiServerConnection(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.num_messages_client_received = 0
        self.num_messages_server1_received = 0
        self.num_messages_server2_received = 0

    def test_normal_message(self):
        
        context = zmq.Context()
        
        server1_id = 'test_server_1'
        server2_id = 'test_server_2'
        client_id = 'test_client_1'
        
        # TODO do we need to specify what type of client?
        server1 = ServerInterface(context, server1_id, 'c2s_1')
        server2 = ServerInterface(context, server2_id, 'c2s_2', [69999], all_addresses=True)
        client = ClientInterface(context, client_id)

        # Connect second client after first setup.
        client.wire_locally_to(server1)
        client.wire_remotely_to(server2, '127.0.0.1')

        server1.register_callback('server_test_message', self.callback_server1_test_message)
        server2.register_callback('server_test_message', self.callback_server2_test_message)
        client.register_callback('client_test_message', self.callback_client_test_message)
    
        # Make sure client can be setup first.
        client.setup()
        server1.setup()
        server2.setup()
        
        # Give servers chance to receive introduction from new clients.
        time.sleep(1)
        server1.process_new_messages()
        server2.process_new_messages()
        time.sleep(0.25)
        client.process_new_messages()
        
        # Test that client can send message to both servers at once
        client.send_message_to_all('server_test_message', 'arg1')
        time.sleep(0.25)
        server1.process_new_messages()
        server2.process_new_messages()
        self.assertEqual(self.num_messages_server1_received, 1)
        self.assertEqual(self.num_messages_server2_received, 1)
        
        server1.close()
        server2.close()
        client.close()
        
    def callback_server1_test_message(self, connection, arg1):
        self.num_messages_server1_received += 1
    
    def callback_server2_test_message(self, connection, arg1):
        self.num_messages_server2_received += 1

    def callback_client_test_message(self, connection, arg1, arg2):
        self.num_messages_client_received += 1

if __name__ == '__main__':
    
    unittest.main()