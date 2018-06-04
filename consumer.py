from time import sleep
from ina219 import INA219, DeviceRangeError
import numpy
import json
from web3 import Web3, HTTPProvider
import threading
from hems import Hems
from gpiozero import LED

SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 2.0
SEC_BTWN_READS = 10
EN_THRESHOLD = 10
MMA_N = 50
INA_SAMPLES = 10
INA_ADDRESS = 0x41
CONSUMPTION_DELAY = 2

class ConsumerMeter (threading.Thread):
    def __init__(self, thread_id, name, event, consumer_id):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = name
        self.event = event
        self.consumer_id = consumer_id

        self.local_energy_consumed = 0.0
        
        self.mmaPowerSum = 0.0
        self.mmaPower = 0.0
        
        if (consumer_id == 1):
            self.led = LED(16)
        else:
            self.led = LED(26)

        self.ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=INA_ADDRESS)
        self.ina.configure(voltage_range=ina.RANGE_32V,
                           gain=ina.GAIN_AUTO,
                           bus_addc=ina.ADC_128SAMP,
                           shunt_adc=ina.ADC_128SAMP)

        self.contract_instance = None
        self.setup_web3()
    
    def run(self):
        print("CONS{}: Consumer running".format(self.consumer_id))
        avail_energy = self.contract_instance.functions.getAvailableEnergy().call()

        isRegistered = self.contract_instance.functions.isRegistered(self.eth_account).call()
        if isRegistered != True:
            txHash = self.contract_instance.functions.registerUser().transact({"from": self.eth_account})
        
        coin_balance = self.contract_instance.functions.getCoinBalance(self.eth_account).call()
        print("CONS{}: Available energy: {}. Coin balance = {}".format(self.consumer_id, avail_energy, coin_balance))
        
        #def handle_event(e):
        #    print("Args for caught event {} are:\n{}".format(e['event'], e['args']))
        
        #Preload Power MMA
        #self.preload_mma()

        while not self.event.is_set():
            _ = self.read_ina219()

            new_entries = self.generated_event_filter.get_new_entries()
            if (len(new_entries) != 0):
                #print("CONS{}: Caught generation event filter entries: {}".format(self.consumer_id, new_entries))
                for e in new_entries:
                    self.handle_generation_event(e)

            new_entries = self.auction_end_event_filter.get_new_entries()
            if (len(new_entries) != 0):
                print("CONS{}: Caught end auction event filter entries: {}".format(self.consumer_id, new_entries))                
                for e in new_entries:
                    self.handle_auction_end_event(e)

            sleep(SEC_BTWN_READS)
            
    def handle_generation_event(self, e):
        if (self.contract_instance != None):
            avail_energy = self.contract_instance.functions.getAvailableEnergy().call()
            print("CONS{}: Energy generated caught. Available energy: {}".format(self.consumer_id, avail_energy))
        
            auction_id = int(e['args']['auctionId'])
            nrg_amt = int(e['args']['quantity'])
            bid_amt = Hems.get_bid(nrg_amt)
            
            highest_current_bid = self.contract_instance.functions.getHighestBid(auction_id).call()

            print("CONS{}: Bidding {} in auction {}. Highest current bid is {}".format(self.consumer_id, bid_amt, auction_id, highest_current_bid))

            hash = self.contract_instance.functions.bidForEnergy(auction_id, bid_amt).transact({'from': self.eth_account})
            receipt = self.w3.eth.getTransactionReceipt(hash)
            rich_logs = self.contract_instance.events.BidIncreased().processReceipt(receipt)
            print("CONS{}: logs from bid_increased: {}".format(self.consumer_id, rich_logs))
            if (len(rich_logs) != 0):
                coin_balance = self.contract_instance.functions.getCoinBalance(self.eth_account).call()
                print("CONS{}: Bid increased: Updated coin balance = {}".format(self.consumer_id, coin_balance))

    def handle_auction_end_event(self, e):
        if (self.contract_instance != None):
            highest_bidder = e['args']['highestBidder']
            auction_id = e['args']['auctionId']
            if (highest_bidder == self.eth_account):
                print("CONS{}: Wins auction {} with bid of {}".format(self.consumer_id, auction_id, e['args']['highestBid']))
                
                self.led.on()
                self.measure_consumption()
                self.led.off()
                hash = self.contract_instance.functions.buyerApprove(auction_id).transact({'from': self.eth_account})
                

    def setup_web3(self):
        #self.w3 = Web3(HTTPProvider('http://localhost:8545'))
        self.w3 = Web3(HTTPProvider('http://localhost:8545'))
        print("CONS{}: Connected to web3:{}".format(self.consumer_id, self.w3.eth.blockNumber))
        self.eth_account = self.w3.eth.accounts[self.consumer_id]
        #self.eth_account = self.w3.personal.listAccounts[self.consumer_id]
        print("CONS{}: Eth account: {}".format(self.consumer_id, self.eth_account))

        with open('./EnergyMarket.json', 'r') as f:
            energy_contract = json.load(f)
            plain_address = '0x4e0e4fc3ef63e8768ad9e43caa1d1bc7d6d35439'
            checksum_address = self.w3.toChecksumAddress(plain_address)
            self.contract_instance = self.w3.eth.contract(address=plain_address, abi=energy_contract["abi"])

            #print("CONS{}: Contract events:\n{}".format(self.consumer_id, self.contract_instance.events.EnergyGenerated))

            #self.generated_event_filter = self.contract_instance.events.EnergyGenerated.createFilter(fromBlock='latest')
            self.generated_event_filter = self.contract_instance.eventFilter('EnergyGenerated', filter_params={'fromBlock': 'latest', 'toBlock': 'latest'})
            self.auction_end_event_filter = self.contract_instance.eventFilter('AuctionEnded', filter_params={'fromBlock': 'latest', 'toBlock': 'latest'})

        
    def measure_consumption(self):
        energy_consumed = 0.0
        while int(energy_consumed) < EN_THRESHOLD:
            p = self.read_ina219()
            energy_consumed += CONSUMPTION_DELAY * p

            #energy_consumed += CONSUMPTION_DELAY * self.mmaPower
            #self.ina.sleep()
            sleep(CONSUMPTION_DELAY)
            #self.ina.wake()


    def read_ina219(self):
        try: 
            p = self.ina.power()
            # self.update_mma()
            return p
        except DeviceRangerError as e:
            print("CONS{}: Device ranger error".format(self.consumer_id))
            return 0


    def update_mma(self):
        for i in range(INA_SAMPLES):
            try:
                p = self.ina.power()
            except DeviceRangerError as e:
                continue
            else:
                self.mmaPowerSum -= self.mmaPower
                self.mmaPowerSum += p
                self.mmaPower = self.mmaPowerSum / MMA_N


    def preload_mma(self):
        for i in range(MMA_N):
            self.mmaPowerSum += self.ina.power()
        
        self.mmaPower = mmaPowerSum / MMA_N

