import zmq
import socket
import os
import time

port_num = 50002
socks = []

context = zmq.Context()

zmq_sock1 = context.socket(zmq.PAIR)
zmq_sock2 = context.socket(zmq.PAIR)

zmq_sock1.connect('inproc://test1')
zmq_sock2.bind('inproc://test1')

zmq_sock1.send_json('mmm')

print "passed"