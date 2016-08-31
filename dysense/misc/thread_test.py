
import time
from threading import Thread

class MyThread(Thread):
    
    def __init__(self):
        super(MyThread, self).__init__()
        self.x = 0
        
    def __del__(self):
        print 'deleted'
        
    def run(self):
        
        try:
            self.run_loop()
        except:
            print 'except'
        finally:
            #self.run_loop()
            print 'finally'
        
    def run_loop(self):
        
        while True:
            print self.x
            self.x += 1
            
            if self.x > 5:
                raise ValueError("Some Error")
            
            time.sleep(0.5)
        
my_thread = MyThread()
my_thread.run()