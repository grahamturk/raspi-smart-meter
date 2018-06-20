from web3 import Web3, HTTPProvider

w3 = Web3(HTTPProvider('http://f6f7b120.ngrok.io'))

print(w3.eth.blockNumber)
