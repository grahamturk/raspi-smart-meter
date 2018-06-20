from prosumer import ProsumerMeter
from consumer import ConsumerMeter
from flask_server import FlaskServer
import threading

if __name__ == "__main__":
    terminate = threading.Event()
    try:
        # Create thread locks for atomic reads
        threadLock = threading.Lock()
        consLock = threading.Lock()
        
        threads = []

        # Create and start threads for market participants and flask server
        prosumer_thread = ProsumerMeter(1, "PSM-Thread", threadLock, terminate)
        consumer_thread_1 = ConsumerMeter(2, "CSM-Thread-1", terminate, 1, consLock)
        consumer_thread_2 = ConsumerMeter(3, "CSM-Thread-2", terminate, 2, consLock)
        server_thread = FlaskServer(3, "FS_Thread", prosumer_thread, threadLock, terminate)
        
        server_thread.start()
        prosumer_thread.start()
        consumer_thread_1.start()
        consumer_thread_2.start()
        
        threads.append(prosumer_thread)
        threads.append(consumer_thread_1)
        threads.append(consumer_thread_2)
        threads.append(server_thread)
        
        # Defer execution to threads by blocking this thread
        for t in threads:
            t.join()
                
        print("Exiting main thread")

    except KeyboardInterrupt:
        print("\nCtrl-C pressed")
        terminate.set()
    
