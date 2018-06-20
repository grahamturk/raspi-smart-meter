import random
from time import sleep

# Bidding module
class Hems:
    # Return a bid based on the amount of energy offered in this auction
    def get_bid(amt):
        sleep(random.randint(1, 3))
        return random.randint(1, 10)
        
