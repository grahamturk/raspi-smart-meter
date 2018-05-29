from flask import Flask, jsonify
import threading
from time import sleep

class FlaskServer (threading.Thread):
    def __init__(self, threadID, name, meter, threadLock, event):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.meter = meter
        self.tLock = threadLock
        self.event = event
        
        self.app = Flask(__name__)
        self.app.add_url_rule('/', 'index', self.hello_world, methods=['GET'])
        self.app.add_url_rule('/solar', 'solar', self.get_data, methods=['GET'])
        
    def run(self):
        self.app.run(host='0.0.0.0')

    def hello_world(self):
        return 'Hello, world!'

    def get_data(self):
        self.tLock.acquire()
        try:
            print("inside get data")
            data = self.meter.grab_data()
            
            return jsonify(voltage=data['voltage'],
                           current=data['current'],
                           power=data['power'],
                           time=data['time'])

        except (IndexError, IOError) as e:
            return jsonify({'error': e.message}), 503

        finally:
            self.tLock.release()

