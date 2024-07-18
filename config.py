import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# network configuration
NETWORK_URL = os.getenv('NETWORK_URL', 'http://ganache:8545')

# Contract address
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
CONTRACT_ABI = os.getenv('CONTRACT_ABI')

# Wallet configuration
PRODUCER_PRIVATE_KEY = os.getenv('PRODUCER_PRIVATE_KEY')
PRODUCER_WALLET_ADDRESS = os.getenv('PRODUCER_WALLET_ADDRESS')
CONSUMER_WALLET_ADDRESS = os.getenv('CONSUMER_WALLET_ADDRESS')
CONSUMER_PRIVATE_KEY = os.getenv('CONSUMER_PRIVATE_KEY')

# Other configurations
STORE_SERVICE_URL = os.getenv('STORE_SERVICE_URL', 'http://store:8001')
STREAM_SERVICE_URL = os.getenv('STREAM_SERVICE_URL', 'http://stream:8002')
TRANSACT_SERVICE_URL = os.getenv('TRANSACT_SERVICE_URL', 'http://transact:8003')

def get_web3_url():
    return NETWORK_URL
    
# Web3 setup
w3 = Web3(Web3.HTTPProvider(NETWORK_URL))