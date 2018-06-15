# raspi-smart-meter

## Pre-installation instructions
1. [Install geth](https://geth.ethereum.org/downloads/)
2. ```geth --datadir=/path/to/chaindata --rinkeby --syncmode "light" --rpc --rpcapi db,eth,net,web3,personal``` where chaindata is an empty folder
3. Create three accounts using `geth account new` and enter a secure passphrase
4. Get some test ether for your accounts at <https://www.rinkeby.io/#faucet>
5. Stop running instance with `Ctrl-C`

## Installation instructions
1. `git clone https://github.com/grahamturk/raspi-smart-meter.git`
2. Setup virtual environment with python 3.5+ following (these instructions)[http://web3py.readthedocs.io/en/stable/troubleshooting.html#setup-environment]
3. `source /path/to/venv/bin/activate`
4. `pip install -r requirements.txt`
5. `git checkout osx-testing` (for desktop testing)
6. Create private local file `addresses.py`and fill in the following fields
```CONTRACT_ADDR = '0x0f8f7f94d13d15007b42b6622858e080825b5646'
   PROS_PASS = 'passphrase for eth.accounts[0]'
   CONS1_PASS = 'passphrase for eth.accounts[1]'
   CONS2_PASS = 'passphrase for eth.accounts[2]'
```
7. Deactivate venv with `deactivate`

## Running instructions
1. `geth --datadir=/path/to/chaindata --rinkeby --syncmode "light" --rpc --rpcapi db,eth,net,web3,personal`
2. In a separate tab where `pwd==raspi-smart-meter`
   1. `source /path/to/venv/bin/activate`
   2. `python main.py`
