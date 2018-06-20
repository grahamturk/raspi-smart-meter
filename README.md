# raspi-smart-meter

A blockchain-enabled smart meter running on a Raspberry Pi. Uses the Web3 Python library to connect to a local running geth instance and participate in energy auctions managed by a smart contract (deployed)[https://rinkeby.etherscan.io/address/0x0f8f7f94d13d15007b42b6622858e080825b5646] to the Rinkeby test network.

Requires a 32+ GB SD card with Raspian operating system installed. Instructions for downloading Raspbian to a blank SD card can be found (here)[https://www.raspberrypi.org/documentation/installation/noobs.md].

## Pre-installation instructions
1. Wget the latest version of geth for linux at <https://geth.ethereum.org/downloads/>
2. `tar -xvf [geth_version].tar.gz`
3. `cd [geth-version]`
4.  Copy binary folder to `/bin` with `sudo mv geth /usr/local/bin/`
5. ```geth --datadir=/path/to/chaindata --rinkeby --syncmode "light" --rpc --rpcapi db,eth,net,web3,personal``` where chaindata is an empty folder
6. Create three accounts using `geth account new` and enter a secure passphrase
7. Get some test ether for your accounts at <https://www.rinkeby.io/#faucet>
8. Stop running instance with `Ctrl-C`

## Installation instructions
1. `git clone https://github.com/grahamturk/raspi-smart-meter.git`
2. Setup virtual environment with python 3.5+ following (these instructions)[http://web3py.readthedocs.io/en/stable/troubleshooting.html#setup-environment]
3. `source /path/to/venv/bin/activate`
4. `pip install -r requirements.txt`
5. Create private local file `addresses.py`and fill in the following fields
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
