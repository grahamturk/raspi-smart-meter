from flask import Flask, jsonify
import threading

class FlaskServer (threading.Thread):
    def __init__(self, threadID, name, meter, threadLock, event):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.meter = meter
        self.tLock = threadLock
        self.event = event
        
        # Set up app instance and routes
        self.app = Flask(__name__)
        self.app.add_url_rule('/', 'index', self.hello_world, methods=['GET'])
        self.app.add_url_rule('/solar', 'solar', self.get_data, methods=['GET'])
        
    # Triggered when start() method of thread is called
    def run(self):
        self.app.run(host='0.0.0.0')

    # Index route handler
    def hello_world(self):
        return 'Hello, world!'


    # Solar endpoint route handler
    # Returns live meter reads from the INA219
    def get_data(self):
        self.tLock.acquire()
        try:
            data = self.meter.grab_data()
            
            return jsonify(voltage=data['voltage'],
                           current=data['current'],
                           power=data['power'],
                           time=data['time'])

        except (IndexError, IOError) as e:
            return jsonify({'error': e.message}), 503

        finally:
            self.tLock.release()

