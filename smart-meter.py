import time
import json
from web3 import Web3, HTTPProvider
import threading
from Adafruit_IO import *
import addresses
from web3.middleware import geth_poa_middleware

SEC_BTWN_READS = 5
EN_THRESHOLD = 30
AIO = Client('6213a24ec9144493911762e9798b61d0')

class SmartMeter:
    def __init__(self):
        self.local_energy_stored = 0.0
        self.energy_balance = 0.0
        self.coin_balance = 0.0

        self.contract_instance = None
        self.setup_web3()

    # Setup all web3-related functionality
    def setup_web3(self):
        # Either remote node (HTTPProvider) or local Rinkeby (IPCProvider)
        self.w3 = Web3(HTTPProvider(addresses.NGROK_URL))
        #self.w3 = Web3(IPCPProvider('/Users/turkg/Library/Ethereum/rinkeby/geth.ipc'))
        
        # Required for web3.py when using POA chains
        # self.w3.middleware_stack.inject(geth_poa_middleware, layer=0)
        
        self.eth_account = self.w3.eth.accounts[0]
        
        # Initialize smart contract
        with open('./EnergyMarket.json', 'r') as f:
            energy_contract = json.load(f)
            plain_address = addresses.CONTRACT_ADDR
            checksum_address = self.w3.toChecksumAddress(plain_address)
            self.contract_instance = self.w3.eth.contract(address=checksum_address, abi=energy_contract["abi"])

            # Configure event handlers
            self.generated_event_filter = self.contract_instance.events.EnergyGenerated.createFilter(fromBlock='latest', toBlock='latest')
            self.bid_increased_event_filter = self.contract_instance.events.BidIncreased.createFilter(fromBlock='latest', toBlock='latest')
            self.auction_end_event_filter = self.contract_instance.events.AuctionEnded.createFilter(fromBlock='latest', toBlock='latest')
            self.consumed_event_filter = self.contract_instance.events.EnergyConsumed.createFilter(fromBlock='latest', toBlock='latest')

    def run(self):
        if (self.contract_instance == None):
            sys.stdout.write("Contract not initialized")
            return
        
        # Register user if not already registered
        isRegistered = self.contract_instance.functions.isRegistered(self.eth_account).call()
        if isRegistered != True:
            txHash = self.contract_instance.functions.registerUser().transact({"from": self.eth_account})
        else:
            self.energy_balance = self.contract_instance.functions.getEnergyBalance(self.eth_account).call()
            self.coin_balance = self.contract_instance.functions.getCoinBalance(self.eth_account).call()

        # Run until interrupted
        while True:
            # Unlock account on each iteration so never gets locked out
            self.w3.personal.unlockAccount(self.eth_account, addresses.PROS_PASS)
            
            reading = sensor.read()
            self.local_energy_stored += reading

            if (int(self.local_energy_stored > EN_THRESHOLD)):
                self.send_generate()
            
            new_generation_entries = self.generated_event_filter.get_new_entries()
            for e in new_generation_entries:
                self.handle_generation_event(e)
            
            new_bid_increased_entries = self.bid_increased_event_filter.get_new_entries()
            for e in new_bid_increased_entries:
                self.handle_bid_increased_event(e)
                
            new_auction_end_entries = self.auction_end_event_filter.get_new_entries()
            for e in new_auction_end_entries:
                self.handle_auction_end_event(e)

            new_consumed_entries = self.consumed_event_filter.get_new_entries()
            for e in new_consumed_entries:
                self.handle_consumed_event(e)

            time.sleep(SEC_BTWN_READS)
        
    # If created the auction, trigger delayed termination
    # Else bid based on HEMS strategy
    def handle_generation_event(self, e):
        # Bid on auction based on customizable auction strategy
        auction_id = int(e['args']['auctionId'])
        if (e['args']['createdBy'] == self.eth_account):
            # TODO: check auctionId is an integer
            self.energy_balance = self.contract_instance.functions.getEnergyBalance(self.eth_account).call()
            t = threading.Timer(10.0, self.end_auction, [auctionId])
            t.start()
        else:
            nrg_amt = int(e['args']['quantity'])
            self.nrg_amts[auctionId] = nrg_amt

            highest_current_bid = self.contract_instance.functions.getHighestBid(auction_id).call()

            bid_amt = self.hems.get_bid(nrg_amt, highest_current_bid)
            if bid_amt > 0:
                hash = self.contract_instance.functions.bidForEnergy(auction_id, bid_amt).transact({'from': self.eth_account})
    
    # If this meter is not highest bidder, give chance to re-bid
    def handle_bid_increased_event(self, e):
        if (e['args']['bidder'] != self.eth_account):
            bid_amt = self.hems.get_bid(self.nrgs[amts], e['args']['amount'])
            if bid_amt > 0:
                hash = self.contract_instance.functions.bidForEnergy(e['args']['auction_id'], bid_amt).transact({'from': self.eth_account})
        else:
            self.coin_balance = self.contract_instance.functions.getCoinBalance(self.eth_account).call()

    # If this meter won the auction, begin measuring consumption for approval
    def handle_auction_end_event(self, e):
        highest_bidder = e['args']['highestBidder']
        auction_id = e['args']['auctionId']
        quantity = e['args']['quantity']

        if (highest_bidder == self.eth_account):
            self.sensor.measure_consumption(quantity)            
            hash = self.contract_instance.functions.buyerApprove(auction_id).transact({'from': self.eth_account})    

    # If consumed energy came from an auction generated by self, update coin and energy balances
    def handle_consumed_event(self, e):
        if (e['args']['createdBy'] == self.eth_account):
            coin_balance = self.contract_instance.functions.getCoinBalance(self.eth_account).call()
            energy_balance = self.contract_instance.functions.getEnergyBalance(self.eth_account).call()

    # Start a new auction
    def send_generate(self):
        hash = self.contract_instance.functions.generateEnergy(int(self.local_energy_stored), 10).transact({"from": self.eth_account})
        self.local_energy_stored = 0

    # Trigger the end of auction number auctionId
    def end_auction(self, auctionId):
        hash = self.contract_instance.functions.endAuction(auctionId).transact({'from': self.eth_account})

    # Grab energy and coin balances
    def get_balances(self):
        balances = {'energy': self.energy_balance, 'coin': self.coin_balance}
        return balances
        
# TODO: put all INA functionality in sensor module (including exception handling)
# TODO: lock around grabbing energy balances    

