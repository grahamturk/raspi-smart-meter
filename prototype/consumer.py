from time import sleep
from ina219 import INA219, DeviceRangeError
import json
from web3 import Web3, HTTPProvider
import threading
from hems import Hems
from gpiozero import LED
import addresses
from web3.middleware import geth_poa_middleware

SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 2.0
SEC_BTWN_READS = 3
EN_THRESHOLD = 50
MMA_N = 50
INA_SAMPLES = 10
INA_ADDRESS = 0x41
CONSUMPTION_DELAY = 1

class ConsumerMeter (threading.Thread):
    # consumer_id used to differentiate between 
    # two consumers reading from same INA219 sensor
    def __init__(self, thread_id, name, event, consumer_id, consLock):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.name = name
        self.event = event
        self.consumer_id = consumer_id
        self.cLock = consLock

        self.local_energy_consumed = 0.0
        
        self.mmaPowerSum = 0.0
        self.mmaPower = 0.0
        
        if (consumer_id == 1):
            self.led = LED(16)
        else:
            self.led = LED(26)

        self.ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=INA_ADDRESS)
        self.ina.configure(voltage_range=self.ina.RANGE_32V,
                           gain=self.ina.GAIN_AUTO,
                           bus_adc=self.ina.ADC_128SAMP,
                           shunt_adc=self.ina.ADC_128SAMP)

        self.contract_instance = None
        self.setup_web3()
    
    # Method called when thread is started
    # Respond to incoming blockchain events
    def run(self):
        if (self.contract_instance == None):
            print("Contract not initialized")
            return

        avail_energy = self.contract_instance.functions.getAvailableEnergy().call()
        print("CONS{}: Consumer running. Available energy = {}".format(self.consumer_id, avail_energy))        

        # Register user if not already registered
        isRegistered = self.contract_instance.functions.isRegistered(self.eth_account).call()
        if isRegistered != True:
            txHash = self.contract_instance.functions.registerUser().transact({"from": self.eth_account})
        else: # Fetch initial coin balance
            coin_balance = self.contract_instance.functions.getCoinBalance(self.eth_account).call()
            print("CONS{}: Coin balance = {}".format(self.consumer_id, coin_balance))
        
        # Preload Power MMA
        #self.preload_mma()

        # Uncomment if INA power consumption is a concern
        # self.ina.sleep()

        # Run until interrupted from main thread
        while not self.event.is_set():
            #_ = self.read_ina219()

            # Unlock account on each iteration
            if (self.consumer_id == 1):
                self.w3.personal.unlockAccount(self.eth_account, addresses.CONS1_PASS)
            else:
                self.w3.personal.unlockAccount(self.eth_account, addresses.CONS2_PASS)

            # Fetch log event entries and respond accordingly
            new_generation_entries = self.generated_event_filter.get_new_entries()
            if (len(new_generation_entries) != 0):
                for e in new_generation_entries:
                    self.handle_generation_event(e)

            new_auction_end_entries = self.auction_end_event_filter.get_new_entries()
            if (len(new_auction_end_entries) != 0):
                print("CONS{}: Caught end auction event filter entries: {}".format(self.consumer_id, new_auction_end_entries))                
                for e in new_auction_end_entries:
                    self.handle_auction_end_event(e)

            new_bid_increased_entries = self.bid_increased_event_filter.get_new_entries()
            if (len(new_bid_increased_entries) != 0):
                for e in new_bid_increased_entries:
                    self.handle_bid_increased_event(e)

            sleep(SEC_BTWN_READS)
            
    # Receive a new auction and submit bid
    def handle_generation_event(self, e):
        avail_energy = self.contract_instance.functions.getAvailableEnergy().call()
        print("CONS{}: Energy generated caught. Available energy: {}".format(self.consumer_id, avail_energy))
        
        # Bid on auction based on customizable auction strategy
        auction_id = int(e['args']['auctionId'])
        nrg_amt = int(e['args']['quantity'])
        bid_amt = Hems.get_bid(nrg_amt)
        
        highest_current_bid = self.contract_instance.functions.getHighestBid(auction_id).call()
        print("CONS{}: Bidding {} in auction {}. Highest current bid is {}".format(self.consumer_id, bid_amt, auction_id, highest_current_bid))
        
        hash = self.contract_instance.functions.bidForEnergy(auction_id, bid_amt).transact({'from': self.eth_account})

        # Only ganache because transaction will not be mined immediately in Rinkeby
        '''
        receipt = self.w3.eth.getTransactionReceipt(hash)
        rich_log = self.contract_instance.events.BidIncreased().processReceipt(receipt)[0]
        print("CONS{}: logs from bid_increased: {}".format(self.consumer_id, rich_log))
        '''

    # If this consumer won the auction, begin measuring consumption for approval
    def handle_auction_end_event(self, e):
        highest_bidder = e['args']['highestBidder']
        auction_id = e['args']['auctionId']
        quantity = e['args']['quantity']

        if (highest_bidder == self.eth_account):
            print("CONS{}: Wins auction {} with bid of {}; quantity = {}".format(self.consumer_id, auction_id, e['args']['highestBid'], quantity))            
            
            # Uncomment if power consumption is a concern
            #self.ina.wake()
            self.led.on()
            self.measure_consumption(quantity)
            self.led.off()
            # Uncomment if power consumption is a concern
            # self.ina.sleep()
            
            hash = self.contract_instance.functions.buyerApprove(auction_id).transact({'from': self.eth_account})
           
    # If this consumer is new highest bidder, update coin balance        
    def handle_bid_increased_event(self, e):
        if (e['args']['bidder'] == self.eth_account):
            coin_balance = self.contract_instance.functions.getCoinBalance(self.eth_account).call()
            print("CONS{}: Bid increased: Updated coin balance = {}".format(self.consumer_id, coin_balance))

    # Setup all web3-related functionality (web3 instance, eth account, contract instance)
    def setup_web3(self):
        # Either remote node (HTTPProvider) via NGROK or local Rinkeby node (IPCProvider)
        self.w3 = Web3(HTTPProvider(addresses.NGROK_URL))
        #self.w3 = Web3(IPCProvider('/Users/turkg/Library/Ethereum/rinkeby/geth.ipc'))
        
        # Required for web3.py using POA chains
        self.w3.middleware_stack.inject(geth_poa_middleware, layer=0)

        # Rinkeby
        self.eth_account = self.w3.eth.accounts[self.consumer_id + 1]
        # Ganache
        #self.eth_account = self.w3.eth.accounts[self.consumer_id]

        print("CONS{}: Connected to web3:{}".format(self.consumer_id, self.w3.eth.blockNumber))
        print("CONS{}: Eth account: {}".format(self.consumer_id, self.eth_account))

        # Initialize smart contract and set up event handlers
        with open('./EnergyMarket.json', 'r') as f:
            energy_contract = json.load(f)
            plain_address = addresses.CONTRACT_ADDR
            checksum_address = self.w3.toChecksumAddress(plain_address)
            self.contract_instance = self.w3.eth.contract(address=checksum_address, abi=energy_contract["abi"])

            #new syntax
            self.generated_event_filter = self.contract_instance.events.EnergyGenerated.createFilter(fromBlock='latest', toBlock='latest')
            self.auction_end_event_filter = self.contract_instance.events.AuctionEnded.createFilter(fromBlock='latest', toBlock='latest')
            self.bid_increased_event_filter = self.contract_instance.events.BidIncreased.createFilter(fromBlock='latest', toBlock='latest')

    # Measure consumption until total exceeds quanity        
    def measure_consumption(self, quantity):
        energy_consumed = 0.0
        while int(energy_consumed) < quantity:
            p = self.read_ina219()
            energy_consumed += CONSUMPTION_DELAY * p
            
            print('CONS{} power: {}'.format(self.consumer_id, p))
            print('CONS{} Energy consumed: {}'.format(self.consumer_id, energy_consumed))

            #energy_consumed += CONSUMPTION_DELAY * self.mmaPower
            
            sleep(CONSUMPTION_DELAY)

    # Perform meter reads        
    def read_ina219(self):
        self.cLock.acquire()
        try:
            p = self.ina.power()
            # self.update_mma()
            
            # Uncomment if just testing web3 functionality
            # p = 8
            
            return p
        except DeviceRangerError as e:
            print("CONS{}: Device ranger error".format(self.consumer_id))
            return 0
        finally:
            self.cLock.release()

    # Obtain a set of readings to initialize MMA
    def preload_mma(self):
        for i in range(MMA_N):
            self.mmaPowerSum += self.ina.power()
        
        self.mmaPower = mmaPowerSum / MMA_N

    # Update MMA values by collecting a new set of readings
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

