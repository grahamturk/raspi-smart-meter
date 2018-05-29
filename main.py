from prosumer import ProsumerMeter
from consumer import ConsumerMeter
from flask_server import FlaskServer
import threading

if __name__ == "__main__":
    terminate = threading.Event()
    try:
        threadLock = threading.Lock()
        
        threads = []
        
        prosumer_thread = ProsumerMeter(1, "PSM-Thread", threadLock, terminate)
        consumer_thread_1 = ConsumerMeter(2, "CSM-Thread-1", terminate, 1)
        consumer_thread_2 = ConsumerMeter(3, "CSM-Thread-2", terminate, 2)
        server_thread = FlaskServer(3, "FS_Thread", prosumer_thread, threadLock, terminate)
        
        server_thread.start()
        prosumer_thread.start()
        consumer_thread_1.start()
        consumer_thread_2.start()
        
        threads.append(prosumer_thread)
        threads.append(consumer_thread_1)
        threads.append(consumer_thread_2)
        threads.append(server_thread)
        
        for t in threads:
            t.join()
                
        print("Exiting main thread")

    except KeyboardInterrupt:
        print("\nCtrl-C pressed")
        terminate.set()
    
