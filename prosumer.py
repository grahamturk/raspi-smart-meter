from time import sleep
import time
from ina219 import INA219, DeviceRangeError
import json
from web3 import Web3, HTTPProvider
import threading
import random
from Adafruit_IO import *

SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 1.0
SEC_BTWN_READS = 4
EN_THRESHOLD = 4000
MMA_N = 50
INA_SAMPLES = 10
INA_ADDRESS = 0x40
AIO = Client('6213a24ec9144493911762e9798b61d0')

class ProsumerMeter (threading.Thread):
    def __init__(self, threadID, name, threadLock, event):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.tLock = threadLock
        self.event = event

        self.data = {"voltage": 0.0, "current": 0.0, "power": 0.0, "time": time.time()}
        self.local_energy_stored = 0.0

        self.mmaCurrentSum = 0.0
        self.mmaCurrent = 0.0
        self.mmaVoltageSum = 0.0
        self.mmaVoltage = 0.0
        self.mmaPowerSum = 0.0
        self.mmaPower = 0.0

        self.ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=INA_ADDRESS)
        self.ina.configure(voltage_range=self.ina.RANGE_32V,
                           gain=self.ina.GAIN_AUTO,
                           bus_addc=self.ina.ADC_128SAMP,
                           shunt_adc=self.ina.ADC_128SAMP)

        self.contract_instance = None
        self.setup_web3()
    
    def run(self):
        print("PROS: Prosumer running")
        avail_energy = self.contract_instance.functions.getAvailableEnergy().call()

        isRegistered = self.contract_instance.functions.isRegistered(self.eth_account).call()
        if isRegistered != True:
            txHash = self.contract_instance.functions.registerUser().transact({"from": self.eth_account})
        
        coin_balance = self.contract_instance.functions.getCoinBalance(self.eth_account).call()
        print("PROS: Available energy: {}. Coin balance: {}".format(avail_energy, coin_balance))
        
        # Preload MMAs
        #self.preload_mma()
        
        while not self.event.is_set():
            self.read_ina219()
            #self.ina.sleep()
            
            new_entries = self.consumed_event_filter.get_new_entries()
            for e in new_entries:
                self.handle_consumed_event(e)
                
            #for block in self.block_filter.get_new_entries():
            #    print("New lastest block:\n{}".format(block))

            sleep(SEC_BTWN_READS)
            #self.ina.wake()

            
    def handle_consumed_event(self, e):
        if (self.contract_instance != None):
            if (e['args']['createdBy'] == self.eth_account):
                coin_balance = self.contract_instance.functions.getCoinBalance(self.eth_account).call()
                energy_balance = self.contract_instance.functions.getEnergyBalance(self.eth_account).call()
                print("PROS: Energy consumed on auction {}. Updated coin balance: {}. Updated energy balance: {}".format(int(e['args']['auctionId']), coin_balance, energy_balance))

    def grab_data(self):
        local_data = self.data
        return local_data

    
    def read_ina219(self):
        self.tLock.acquire()
        try:
            v = self.ina.voltage()
            i = self.ina.current()
            p = self.ina.power()

            print('PROS power: {}'.format(p))
            #v = random.randint(1,2)
            #i = random.randint(1,2)
            #p = v * i
            
            self.local_energy_stored += SEC_BTWN_READS * p
            #self.local_energy_stored += p
        
            currentTime = time.time()
            self.data['time'] = currentTime
            self.data['voltage'] = v
            self.data['current'] = i
            self.data['power'] = p

            data = Data(value=p, created_epoch=currentTime)
            AIO.create_data('solardata', data)
            
            print("PROS: power = {}".format(p))

            '''
            self.update_mma()
            self.local_energy_stored += SEC_BTWN_READS * self.mmaPower

            self.data['voltage'] = self.mmaVoltage
            self.data['current'] = self.mmaCurrent
            self.data['power'] = self.mmaPower
            '''

        except DeviceRangeError as e:
            print("PROS: Device range error")

        else:
            #self.tLock.release()
            # check cumulative energy
            # if exceeds watt-hour, send transaction
            if (int(self.local_energy_stored) > EN_THRESHOLD):
                print("PROS: local storage exceeded")
                self.send_generate()
            #self.tLock.acquire()
        
        finally:
            self.tLock.release()
            
    def setup_web3(self):
        #self.w3 = Web3(HTTPProvider('http://localhost:8545'))
        #ngrok address
        self.w3 = Web3(HTTPProvider('http://447df587.ngrok.io')
        
        print("PROS: Connected to web3:{}".format(self.w3.eth.blockNumber))
        self.eth_account = self.w3.eth.accounts[0]
        
        # For running on Rinkeby
        #self.eth_account = self.w3.personal.listAccounts[0]
        print("PROS: Eth account: {}".format(self.eth_account))
    
        with open('./EnergyMarket.json', 'r') as f:
            energy_contract = json.load(f)
            plain_address = '0x4e0e4fc3ef63e8768ad9e43caa1d1bc7d6d35439'
            checksum_address = self.w3.toChecksumAddress(plain_address)
            self.contract_instance = self.w3.eth.contract(address=plain_address, abi=energy_contract["abi"])
            
            #bad one
            #self.event_filter = self.contract_instance.events.EnergyGenerated.createFilter(fromBlock=0, toBlock='latest')
            #good one
            self.event_filter = self.contract_instance.eventFilter('EnergyGenerated', filter_params={'fromBlock': 'latest', 'toBlock': 'latest'})
            
            self.consumed_event_filter = self.contract_instance.eventFilter('EnergyConsumed', filter_params={'fromBlock': 'latest', 'toBlock': 'latest'})

            #self.block_filter = self.w3.eth.filter('latest')
            
    def send_generate(self):
        if (self.contract_instance != None):
            hash = self.contract_instance.functions.generateEnergy(int(self.local_energy_stored), 10).transact({"from": self.eth_account})
            #print("PROS: Hash: {}".format(hash))

            receipt = self.w3.eth.getTransactionReceipt(hash)
            #print("PROS: Receipt: {}".format(receipt))
            
            rich_log = self.contract_instance.events.EnergyGenerated().processReceipt(receipt)[0]
            #print("PROS: Event: {}\n Args: {}".format(rich_log['event'], rich_log['args']))

            self.local_energy_stored = 0
            energy_balance = self.contract_instance.functions.getEnergyBalance(self.eth_account).call()
            print("PROS: Generated receipt. Updated energy balance: {}. Auction id: {}".format(energy_balance, rich_log['args']['auctionId']))

            t = threading.Timer(10.0, self.end_auction, [rich_log['args']['auctionId']])

            t.start()
            print("below t start")

    
    def end_auction(self, auctionId):
        hash = self.contract_instance.functions.endAuction(auctionId).transact({'from': self.eth_account})     
        receipt = self.w3.eth.getTransactionReceipt(hash)
        rich_logs = self.contract_instance.events.AuctionEnded().processReceipt(receipt)
        print("PROS: Auction ended\nEvent: {} Logs: {}".format(rich_logs[0]['event'], rich_logs[0]['args']))


    def preload_mma(self):
        for i in range(MMA_N):
            self.mmaCurrentSum += self.ina.current()
            self.mmaVoltageSum += self.ina.voltage()
            self.mmaPowerSum += self.ina.power()
        
        self.mmaCurrent = mmaCurrentSum / MMA_N
        self.mmaVoltage = mmaVoltageSum / MMA_N
        self.mmaPower = mmaPowerSum / MMA_N


    def update_mma(self):
        for i in range(INA_SAMPLES):
            try: 
                v = self.ina.voltage()
                i = self.ina.current()
                p = self.ina.power() / 1000
            
            except DeviceRangeError as e:
                continue
            
            else: 
                self.mmaCurrentSum -= self.mmaCurrent
                self.mmaCurrentSum += i
                self.mmaCurrent = self.mmaCurrentSum / MMA_N
                
                self.mmaVoltageSum -= self.mmaVoltage
                self.mmaVoltageSum += v
                self.mmaVoltage = self.mmaVoltageSum / MMA_N
                
                self.mmaPowerSum -= self.mmaPower
                self.mmaPowerSum += p
                self.mmaPower = self.mmaPowerSum / MMA_N
