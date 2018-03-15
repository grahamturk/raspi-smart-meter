from smart_meter import SmartMeter
from flask_server import FlaskServer
import threading

if __name__ == "__main__":
    terminate = threading.Event()
    try:
        threadLock = threading.Lock()
        
        threads = []
        
        meter_thread = SmartMeter(1, "SM-Thread", threadLock, terminate)
        server_thread = FlaskServer(2, "FS_Thread", meter_thread, threadLock, terminate)
        
        server_thread.start()
        meter_thread.start()
        
        threads.append(meter_thread)
        threads.append(server_thread)
        
        for t in threads:
            t.join()
                
        print "Exiting main thread"

    except KeyboardInterrupt:
        print ("\nCtrl-C pressed")
        terminate.set()
    
