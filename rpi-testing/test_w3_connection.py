from web3 import Web3, HTTPProvider

w3 = Web3(HTTPProvider('http://82f12ae3.ngrok.io'))

print(w3.eth.blockNumber)
