# config.py
import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()


# Network configuration
NETWORK = os.getenv('NETWORK', 'ganache')  # 'ganache', 'sepolia', etc.

# Ganache configuration
GANACHE_URL = os.getenv('GANACHE_URL', 'http://127.0.0.1:8545')

# Testnet configuration (e.g., Sepolia)
TESTNET_URL = os.getenv('TESTNET_URL', 'https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID')

# Contract address
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
CONTRACT_ABI = os.getenv('CONTRACT_ABI')

# Wallet configuration
WALLET_PRIVATE_KEY = os.getenv('WALLET_PRIVATE_KEY')
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')

# Other configurations
STORE_SERVICE_URL = os.getenv('STORE_SERVICE_URL', 'http://localhost:8001')
STREAM_SERVICE_URL = os.getenv('STREAM_SERVICE_URL', 'http://localhost:8001')
TRANSACT_SERVICE_URL = os.getenv('TRANSACT_SERVICE_URL', 'http://localhost:8001')

def get_web3_url():
    if NETWORK == 'ganache':
        return GANACHE_URL
    else:
        return TESTNET_URL
    
# Web3 setup
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))