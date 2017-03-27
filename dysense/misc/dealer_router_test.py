import zmq
import socket
import os
import time
import json
import sys

from sensor_client import SensorInfo

port_num = 50002
socks = []

class TestData(object):

    def __init__(self, m):

        self.m = m

    @property
    def some_property(self):
        return self.m

context = zmq.Context()

zmq_sock1 = context.socket(zmq.ROUTER)
zmq_sock2 = context.socket(zmq.ROUTER)
zmq_sock3 = context.socket(zmq.DEALER)

zmq_sock1.bind('inproc://s1')
zmq_sock2.bind('inproc://s2')
zmq_sock3.connect('inproc://s1')
zmq_sock3.connect('inproc://s2')

sensor_info = SensorInfo('irt', 'kyle', 1, {'some_setting':23.34})
sensor_info.text_messages.append('text1')
sensor_info.text_messages.append('text2')

zmq_sock3.send(json.dumps({'body': sensor_info.__dict__}))
zmq_sock3.send(json.dumps({'mmm': TestData(23).__dict__}))

print 'sent'

#zmq_sock3.recv_multipart()

multipart_message = zmq_sock1.recv_multipart()
print multipart_message
id = multipart_message[0]
message = json.loads(multipart_message[1])
#id = int(id.encode('hex'), 16)

multipart_message = zmq_sock2.recv_multipart()
print multipart_message
id = multipart_message[0]
message = json.loads(multipart_message[1])

print "done"