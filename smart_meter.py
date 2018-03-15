from time import sleep
from ina219 import INA219
from ina219 import DeviceRangeError
import numpy
from web3 import Web3, HTTPProvider, TestRPCProvider
import threading

SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 2.0
SEC_BTWN_READS = 10
EN_THRESHOLD = 90

class SmartMeter (threading.Thread):
    
    def __init__(self, threadID, name, threadLock, event):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.tLock = threadLock
        self.event = event

        self.data = {"voltage": 0.0, "current": 0.0, "power": 0.0}
        #self.ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS)
        self.local_energy_stored = 0
        '''
        self.ina.configure(voltage_range=ina.RANGE_16V,
                           gain=ina.GAIN_AUTO,
                           bus_addc=ina.ADC_128SAMP,
                           shunt_adc=ina.ADC_128SAMP)
        '''
        self.contract_instance = None
        #self.setup_web3()
    
    def run(self):
        while not self.event.is_set():
            self.read_ina219()
            #self.ina.sleep()
            sleep(SEC_BTWN_READS)
            #self.ina.wake()
            

    def grab_data(self):
        print 'inside grab data'
        local_data = self.data
        return local_data
    
    def read_ina219(self):
        self.tLock.acquire()
        try:
            print 'inside reading'
            #v = self.ina.voltage()
            #i = self.ina.current()
            #p = self.ina.power() / 1000
            v = 3.3
            i = 1
            p = 3.3

            self.local_energy_stored += SEC_BTWN_READS * numpy.mean([p, self.data['power']])

            self.data['voltage'] = v
            self.data['current'] = i
            self.data['power'] = p

        except DeviceRangeError as e:
            print "Device range error"

        else:
            #self.tLock.release()
            # check cumulative energy
            # if exceeds watt-hour, send transaction
            if (self.local_energy_stored > EN_THRESHOLD):
                #self.send_generate()
                print 'local storage exceeded'
            #self.tLock.acquire()
        
        finally:
            self.tLock.release()
    
        
'''
def setup_web3(self):
    self.w3 = Web3(HTTPProvider('http://localhost:8545'))
    self.eth_account = w3.eth.accounts[0]
    
    with open('./EnergyMarket.json', 'r') as f:
        energy_contract = json.load(f)
        self.contract_instance = self.w3.eth.contract(address='', abi=energy_contract.abi)
        
def send_generate(self):
    if (self.contract_instance != None):
        self.contract_instance.transact().generateEnergy(self.local_energy_stored, {from: self.eth_account})
        self.local_energy_stored = 0
'''
