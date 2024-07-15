import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from pydantic import BaseModel, HttpUrl
import logging
import aiohttp
import secrets
import traceback
import binascii
from typing import Dict, Any
from core import did_manager
from core.marketplace import add_data_asset, purchase_data_asset
from config import get_web3_url, CONTRACT_ADDRESS, CONTRACT_ABI, STORE_SERVICE_URL, STREAM_SERVICE_URL, TRANSACT_SERVICE_URL
from web3.exceptions import ContractLogicError

from dotenv import load_dotenv

load_dotenv() 

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
GANACHE_URL = os.getenv("GANACHE_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
STORE_SERVICE_URL = os.getenv("STORE_SERVICE_URL", "http://localhost:8001")
STREAM_SERVICE_URL = os.getenv("STREAM_SERVICE_URL", "http://localhost:8001")
TRANSACT_SERVICE_URL = os.getenv("TRANSACT_SERVICE_URL", "http://localhost:8001")

# Web3 setup
web3 = Web3(Web3.HTTPProvider(GANACHE_URL))

def get_web3():
    return Web3(Web3.HTTPProvider(get_web3_url()))

# Simple in-memory wallet and asset stores
connected_wallets = {}
listed_assets = {}

# Model definitions
class WalletConnect(BaseModel):
    address: str

class WalletAuth(BaseModel):
    address: str
    signature: str

class AssetInput(BaseModel):
    name: str
    description: str
    price: int
    is_stream: bool
    data: str  # IPFS hash for static data or stream ID for streams

class PurchaseInput(BaseModel):
    asset_id: int

class StreamSubscriptionInput(BaseModel):
    stream_id: str

def get_authenticated_wallet_address(wallet_address: str = Header(...)):
    if wallet_address not in connected_wallets or not connected_wallets[wallet_address].get("authenticated"):
        raise HTTPException(status_code=401, detail="Wallet not authenticated")
    return wallet_address

def get_contract(w3: Web3 = Depends(get_web3)):
    contract_abi = CONTRACT_ABI
    contract_address = CONTRACT_ADDRESS
    logger.debug(f"Creating contract instance with address: {contract_address}")
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    logger.debug(f"Contract instance created: {contract}")
    return contract

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/accounts")
async def get_accounts(web3: Web3 = Depends(get_web3)):
    return {"accounts": web3.eth.accounts}

@app.get("/contract-address")
async def get_contract_address():
    return {"address": CONTRACT_ADDRESS}

# 1. Wallet Connection and DID Creation
@app.post("/connect-wallet")
async def connect_wallet(wallet: WalletConnect):
    if not Web3.is_address(wallet.address):
        raise HTTPException(status_code=400, detail="Invalid wallet address")
    
    nonce = secrets.token_hex(32)
    connected_wallets[wallet.address] = {"nonce": nonce}
    
    return {"status": "connected", "wallet_address": wallet.address, "nonce": nonce}

@app.post("/authenticate-wallet")
async def authenticate_wallet(wallet_auth: WalletAuth):
    if wallet_auth.address not in connected_wallets:
        raise HTTPException(status_code=401, detail="Wallet not connected")
    
    nonce = connected_wallets[wallet_auth.address]["nonce"]
    message = f"Authenticate to Data Marketplace with nonce: {nonce}"
    message_hash = encode_defunct(text=message)
    
    try:
        w3 = Web3()  # Create a new Web3 instance
        recovered_address = w3.eth.account.recover_message(message_hash, signature=wallet_auth.signature)
        if recovered_address.lower() != wallet_auth.address.lower():
            raise ValueError("Invalid signature")
        
        # If we reach this point, the signature is valid
        connected_wallets[wallet_auth.address]["authenticated"] = True
        
        # Create a DID for the wallet if it doesn't exist
        if "did" not in connected_wallets[wallet_auth.address]:
            did, key = await did_manager.create_did()
            connected_wallets[wallet_auth.address]["did"] = did
            connected_wallets[wallet_auth.address]["did_key"] = key
        
        # Generate a new nonce for next authentication
        connected_wallets[wallet_auth.address]["nonce"] = secrets.token_hex(32)
        
        return {
            "status": "authenticated",
            "wallet_address": wallet_auth.address,
            "did": connected_wallets[wallet_auth.address]["did"],
            "new_nonce": connected_wallets[wallet_auth.address]["nonce"]
        }
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        connected_wallets[wallet_auth.address]["authenticated"] = False
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

@app.post("/create-did")
async def create_did_endpoint(wallet_address: str = Depends(get_authenticated_wallet_address)):
    try:
        did, key = await did_manager.create_did()
        connected_wallets[wallet_address]["did"] = did
        logger.info(f"Created DID: {did} for wallet: {wallet_address}")
        return {"did": did, "key": key}
    except Exception as e:
        logger.error(f"Error creating DID: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. Data Asset Creation and Listing
@app.post("/add-asset")
async def add_data_asset_endpoint(
    asset: AssetInput,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        if asset.is_stream:
            asset_id = len(listed_assets)
            listed_assets[asset_id] = {
                "owner": wallet_address,
                "name": asset.name,
                "description": asset.description,
                "price": asset.price,
                "is_stream": True,
                "stream_id": asset.data
            }
        else:
            # For static assets, we need to store the data first
            try:
                store_result = await store_data(asset.data)
            except Exception as e:
                error_msg = f"Error storing data: {str(e)}"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
            
            asset_id = len(listed_assets)
            listed_assets[asset_id] = {
                "owner": wallet_address,
                "name": asset.name,
                "description": asset.description,
                "price": asset.price,
                "is_stream": False,
                "ipfs_hash": store_result['ipfs_hash']
            }
        
        # Add asset to blockchain
        try:
            tx_hash = add_data_asset(contract, str(asset_id), asset.price, wallet_address)
        except Exception as e:
            error_msg = f"Error adding asset to blockchain: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        logger.info(f"Added asset: {asset_id} by wallet: {wallet_address}")
        return {"success": True, "asset_id": asset_id, "tx_hash": tx_hash}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error adding asset: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# 3. Asset Purchasing and Stream Subscription
@app.post("/purchase-asset/{asset_id}")
async def purchase_data_asset_endpoint(
    asset_id: int,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        logger.info(f"Attempting to purchase asset {asset_id} for wallet {wallet_address}")
        if asset_id not in listed_assets:
            logger.warning(f"Asset {asset_id} not found")
            return JSONResponse(status_code=404, content={"detail": "Asset not found"})
        
        asset = listed_assets[asset_id]
        if asset['is_stream']:
            logger.warning(f"Attempted to purchase stream asset {asset_id}")
            return JSONResponse(status_code=400, content={"detail": "Cannot purchase a stream. Use /subscribe-stream instead."})
        
        logger.info(f"Calling purchase_data_asset for asset {asset_id}")
        tx_hash = purchase_data_asset(contract, asset_id, wallet_address)
        
        # Convert the tx_hash to a hexadecimal string
        if isinstance(tx_hash, bytes):
            tx_hash = binascii.hexlify(tx_hash).decode('ascii')
        
        logger.info(f"Purchased asset: {asset_id} by wallet: {wallet_address}. TX Hash: {tx_hash}")
        return JSONResponse(status_code=200, content={"success": True, "tx_hash": tx_hash})
    except Exception as e:
        logger.error(f"Error purchasing asset {asset_id}: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": f"Error purchasing asset: {str(e)}"})
    

@app.post("/subscribe-stream")
async def subscribe_stream_endpoint(
    subscription: StreamSubscriptionInput,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    web3: Web3 = Depends(get_web3)
):
    try:
        logger.info(f"Attempting to subscribe to stream {subscription.stream_id} for wallet {wallet_address}")
        
        if not connected_wallets.get(wallet_address, {}).get("authenticated"):
            logger.warning(f"Wallet {wallet_address} not authenticated")
            # Authenticate the wallet if it's not already authenticated
            connected_wallets[wallet_address] = {"authenticated": True}
            if "did" not in connected_wallets[wallet_address]:
                did, key = await did_manager.create_did()
                connected_wallets[wallet_address]["did"] = did
                connected_wallets[wallet_address]["did_key"] = key

        did = connected_wallets[wallet_address]["did"]
        
        # TODO: Implement actual proof generation
        proof = "dummy_proof"
        
        logger.info(f"Attempting to subscribe to stream service")
        subscribe_result = await subscribe_stream(subscription.stream_id, did, proof)
        logger.info(f"Subscribed to stream service. Result: {subscribe_result}")
        
        return JSONResponse(status_code=200, content={"success": True, "subscription": subscribe_result})
    except Exception as e:
        logger.error(f"Error subscribing to stream: {str(e)}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": f"Error subscribing to stream: {str(e)}"})

# 4. Data Access
@app.get("/access-asset/{asset_id}")
async def access_asset_endpoint(
    asset_id: int,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        if asset_id not in listed_assets:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset = listed_assets[asset_id]
        
        # Check ownership using the checkOwnership function

        logger.info(f"Contract address: {contract.address}")
        logger.info(f"Checking ownership for asset {asset_id} (type: {type(asset_id)}) and wallet {wallet_address}")

        try:
            logger.info(f"Checking ownership for asset {asset_id} and wallet {wallet_address}")
            is_owner = contract.functions.checkOwnership(asset_id, wallet_address).call()
            logger.info(f"Ownership check result: {is_owner}")
            if not is_owner:
                raise HTTPException(status_code=403, detail="You do not own this asset")
        except ContractLogicError as e:
            logger.error(f"Contract logic error checking ownership: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error checking asset ownership: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error checking ownership: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unexpected error checking asset ownership: {str(e)}")
        
        if asset['is_stream']:
            # For streams, return the stream ID
            return {"stream_id": asset['stream_id']}
        else:
            # For static assets, return the IPFS hash
            return {"ipfs_hash": asset['ipfs_hash']}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing asset: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error accessing asset: {str(e)}")

# Helper functions for interacting with other services
async def store_data(file_path: str):
    url = f"{STORE_SERVICE_URL}/store"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json={"file_path": file_path}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    response_text = await response.text()
                    error_msg = f"Failed to store data. Status: {response.status}, Response: {response_text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
        except aiohttp.ClientError as e:
            error_msg = f"Error connecting to store service: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

async def retrieve_data(ipfs_hash: str):
    url = f"{STORE_SERVICE_URL}/retrieve"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"ipfs_hash": ipfs_hash}) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise HTTPException(status_code=response.status, detail="Failed to retrieve data")

async def subscribe_stream(stream_id: str, did: str, proof: str):
    url = f"{STREAM_SERVICE_URL}/subscribe"
    payload = {"streamId": stream_id, "did": did, "proof": proof, "data": {}}  # Add an empty data dict
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise HTTPException(status_code=response.status, detail="Failed to subscribe to stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)