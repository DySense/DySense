import socket
import zmq

start = 50000
stop = 51000

passed = 0
failed = 0
failed_nums = []

for port_num in range(start, stop):
    
    context = zmq.Context()
    zmq_sock = context.socket(zmq.ROUTER)
    try:
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', port_num))
        '''
        zmq_sock.bind('tcp://127.0.0.1:{}'.format(port_num))
        passed += 1
    except zmq.ZMQError as e:
        failed += 1
        failed_nums.append(port_num)
    finally:
        #s.close()
        zmq_sock.close()
        
print "Failed {} ({}%)".format(failed, failed * 100.0 / (passed + failed))
print str(failed_nums)