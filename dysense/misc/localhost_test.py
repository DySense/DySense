import zmq
import socket
import os
import time

port_num = 50002
socks = []
#context = zmq.Context()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('127.0.0.1', port_num))

#zmq_sock = context.socket(zmq.ROUTER)

time.sleep(10)

#zmq_sock.bind('tcp://127.0.0.1:{}'.format(port_num))

#socks.append(zmq_sock)
socks.append(s)

print "passed"