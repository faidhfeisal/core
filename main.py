import os
import json
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File, Form
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
import time
from typing import Dict, Any, Optional
from src import did_manager
from src.did_manager import generate_zkproof
from src.marketplace import add_data_asset, purchase_data_asset
from config import get_web3_url, GANACHE_URL, CONTRACT_ADDRESS, CONTRACT_ABI, STORE_SERVICE_URL, STREAM_SERVICE_URL, TRANSACT_SERVICE_URL, WALLET_PRIVATE_KEY
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

class StaticAssetInput(BaseModel):
    name: str
    description: str
    price: int

class StreamAssetInput(BaseModel):
    name: str
    description: str
    price: int
    stream_id: str

class PurchaseInput(BaseModel):
    asset_id: int

class PurchaseRequest(BaseModel):
    message: str

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


# Producer endpoints
@app.post("/producer/add-static-asset")
async def add_static_asset_endpoint(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(...),
    price: int = Form(...),
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        # Store the data first
        try:
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field('file', await file.read(), filename=file.filename)
                async with session.post(f"{STORE_SERVICE_URL}/store", data=form) as response:
                    if response.status == 200:
                        store_result = await response.json()
                        ipfs_hash = store_result['ipfs_hash']
                    else:
                        raise HTTPException(status_code=response.status, detail="Failed to store data")
        except Exception as e:
            error_msg = f"Error storing data: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Add asset to blockchain
        try:
            asset_id, tx_hash = add_data_asset(contract, ipfs_hash, price, wallet_address)
        except Exception as e:
            error_msg = f"Error adding asset to blockchain: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        listed_assets[asset_id] = {
            "owner": wallet_address,
            "name": name,
            "description": description,
            "price": price,
            "is_stream": False,
            "ipfs_hash": ipfs_hash
        }
        
        # Verify the asset was added correctly
        try:
            owner = contract.functions.getAssetOwner(asset_id).call()
            if Web3.to_checksum_address(owner) != Web3.to_checksum_address(wallet_address):
                raise HTTPException(status_code=500, detail=f"Asset owner mismatch. Expected: {wallet_address}, Got: {owner}")
        except ContractLogicError as e:
            if "Asset does not exist" in str(e):
                error_msg = f"Asset {asset_id} was not properly added to the blockchain"
                logger.error(error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
            else:
                raise e
        except Exception as e:
            error_msg = f"Error verifying asset ownership: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        logger.info(f"Added static asset: {asset_id} by wallet: {wallet_address}")
        return {"success": True, "asset_id": asset_id, "tx_hash": tx_hash}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error adding static asset: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    
@app.get("/producer/list-assets")
async def list_assets_endpoint(
    wallet_address: str = Depends(get_authenticated_wallet_address)
):
    try:
        user_assets = [
            {"asset_id": asset_id, **asset_data}
            for asset_id, asset_data in listed_assets.items()
            if asset_data["owner"] == wallet_address
        ]
        return {"success": True, "assets": user_assets}
    except Exception as e:
        logger.error(f"Error listing assets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing assets: {str(e)}")
    
    
@app.get("/producer/asset/{asset_id}")
async def get_asset_endpoint(
    asset_id: int,
    wallet_address: str = Depends(get_authenticated_wallet_address)
):
    try:
        if asset_id not in listed_assets:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset = listed_assets[asset_id]
        if asset["owner"] != wallet_address:
            raise HTTPException(status_code=403, detail="You do not own this asset")
        
        return {"success": True, "asset": {"asset_id": asset_id, **asset}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving asset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving asset: {str(e)}")
    
    
@app.delete("/producer/asset/{asset_id}")
async def delete_asset_endpoint(
    asset_id: int,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        if asset_id not in listed_assets:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset = listed_assets[asset_id]
        logger.info(f"Asset owner from listed_assets: {asset['owner']}")
        logger.info(f"Wallet address trying to delete: {wallet_address}")
        
        if asset["owner"] != wallet_address:
            raise HTTPException(status_code=403, detail="You do not own this asset")
        
        # Check ownership on the blockchain

        owner = contract.functions.getAssetOwner(asset_id).call()
        logger.info(f"Asset owner from blockchain: {owner}")
        is_owner = contract.functions.checkOwnership(asset_id, wallet_address).call()
        logger.info(f"Ownership check on blockchain: {is_owner}")
        
        if not is_owner:
            raise HTTPException(status_code=403, detail="Blockchain ownership check failed")
        
        # Remove asset from blockchain
        try:
            # Ensure the wallet_address is checksum address
            checksum_address = Web3.to_checksum_address(wallet_address)
            logger.debug(f"Checksum address: {checksum_address}")
            
            # Get the nonce for the transaction
            nonce = web3.eth.get_transaction_count(checksum_address)
            
            # Build the transaction
            txn = contract.functions.removeAsset(asset_id).build_transaction({
                'chainId': web3.eth.chain_id,
                'gas': 2000000,
                'gasPrice': web3.eth.gas_price,
                'nonce': nonce,
                'from': checksum_address
            })
            
            # Sign the transaction
            signed_txn = web3.eth.account.sign_transaction(txn, private_key=WALLET_PRIVATE_KEY)
            
            # Send the transaction
            tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            logger.debug(f"Transaction hash: {tx_hash.hex()}")
            
            # Wait for the transaction receipt
            tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            logger.debug(f"Transaction receipt: {tx_receipt}")
            
            if tx_receipt['status'] == 0:
                raise Exception("Transaction failed")
            
        except Exception as e:
            error_msg = f"Error removing asset from blockchain: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Remove asset from local storage
        del listed_assets[asset_id]
        
        # If it's a static asset, remove from IPFS
        if not asset["is_stream"]:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{STORE_SERVICE_URL}/delete", json={"ipfs_hash": asset['ipfs_hash']}) as response:
                        if response.status != 200:
                            logger.warning(f"Failed to delete asset data from IPFS: {await response.text()}")
                        else:
                            logger.info(f"Successfully deleted asset data from IPFS for asset {asset_id}")
            except Exception as e:
                logger.warning(f"Error deleting asset data from IPFS: {str(e)}")
        
        logger.info(f"Deleted asset: {asset_id} by wallet: {wallet_address}")
        return {"success": True, "tx_hash": tx_hash.hex()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting asset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting asset: {str(e)}")

    
@app.post("/producer/create-stream")
async def create_stream_endpoint(
    stream_input: StreamAssetInput,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        asset_id = len(listed_assets)
        listed_assets[asset_id] = {
            "owner": wallet_address,
            "name": stream_input.name,
            "description": stream_input.description,
            "price": stream_input.price,
            "is_stream": True,
            "stream_id": stream_input.stream_id
        }
        
        # Add asset to blockchain
        try:
            tx_hash = add_data_asset(contract, str(asset_id), stream_input.price, wallet_address)
        except Exception as e:
            error_msg = f"Error adding stream to blockchain: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        logger.info(f"Added stream asset: {asset_id} by wallet: {wallet_address}")
        return {"success": True, "asset_id": asset_id, "tx_hash": tx_hash}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error adding stream asset: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
@app.post("/producer/publish-stream/{stream_id}")
async def publish_stream_endpoint(
    stream_id: str,
    data: Dict[str, Any],
    wallet_address: str = Depends(get_authenticated_wallet_address)
):
    try:
        did = connected_wallets[wallet_address]["did"]
        timestamp = int(time.time())
        message = f"{wallet_address}:{stream_id}:{timestamp}"
        proof = await generate_zkproof(did, message)

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{STREAM_SERVICE_URL}/publish", json={
                "stream_id": stream_id,
                "data": data,
                "did": did,
                "proof": proof
            }) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=await response.text())
    except Exception as e:
        logger.error(f"Error publishing to stream: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error publishing to stream: {str(e)}")


# Consumer endpoints
@app.post("/consumer/purchase-asset/{asset_id}")
async def purchase_asset_endpoint(
    asset_id: int,
    purchase_request: PurchaseRequest,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        logger.info(f"Attempting to purchase asset {asset_id} for wallet {wallet_address}")
        
        # Generate ZKP
        try:
            did = connected_wallets[wallet_address]["did"]
            proof = await generate_zkproof(did, purchase_request.message)
        except Exception as e:
            logger.error(f"Error generating ZKProof: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating proof: {str(e)}")
        
        tx_hash = purchase_data_asset(contract, asset_id, wallet_address, proof)
        logger.info(f"Purchased asset: {asset_id} by wallet: {wallet_address}. TX Hash: {tx_hash}")
        return {"success": True, "tx_hash": tx_hash}
    except Exception as e:
        logger.error(f"Error purchasing asset {asset_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error purchasing asset: {str(e)}")
    
@app.post("/consumer/subscribe-stream")
async def subscribe_stream_endpoint(
    subscription: StreamSubscriptionInput,
    wallet_address: str = Depends(get_authenticated_wallet_address)
):
    try:
        logger.info(f"Attempting to subscribe to stream {subscription.stream_id} for wallet {wallet_address}")
        
        did = connected_wallets[wallet_address]["did"]
        timestamp = int(time.time())
        message = f"{wallet_address}:{subscription.stream_id}:{timestamp}"
        proof = await generate_zkproof(did, message)

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{STREAM_SERVICE_URL}/subscribe", json={
                "stream_id": subscription.stream_id,
                "did": did,
                "proof": proof
            }) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=await response.text())
    except Exception as e:
        logger.error(f"Error subscribing to stream: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error subscribing to stream: {str(e)}")
    
@app.get("/consumer/access-static-asset/{asset_id}")
async def access_static_asset_endpoint(
    asset_id: int,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        if asset_id not in listed_assets:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset = listed_assets[asset_id]
        
        if asset['is_stream']:
            raise HTTPException(status_code=400, detail="This endpoint is for static assets only")
        
        # Check ownership using the checkOwnership function
        try:
            is_owner = contract.functions.checkOwnership(asset_id, wallet_address).call()
            if not is_owner:
                raise HTTPException(status_code=403, detail="You do not own this asset")
        except ContractLogicError as e:
            logger.error(f"Contract logic error checking ownership: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error checking asset ownership: {str(e)}")
        
        # Retrieve the data from IPFS
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{STORE_SERVICE_URL}/retrieve", json={"ipfs_hash": asset['ipfs_hash'], "output_path": "temp_file"}) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result['success']:
                            with open("temp_file", "rb") as f:
                                data = f.read()
                            os.remove("temp_file")  # Clean up the temporary file
                            return {"data": data.decode()}
                        else:
                            raise HTTPException(status_code=500, detail="Failed to retrieve data")
                    else:
                        raise HTTPException(status_code=response.status, detail="Failed to retrieve data")
        except Exception as e:
            logger.error(f"Error retrieving data from IPFS: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving data: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing static asset: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error accessing static asset: {str(e)}")

# @app.post("/add-asset")
# async def add_data_asset_endpoint(
#     file: Optional[UploadFile] = File(None),
#     asset: str = Form(...),
#     wallet_address: str = Depends(get_authenticated_wallet_address),
#     contract = Depends(get_contract)
# ):
#     try:
#         asset_data = json.loads(asset)
#         asset_input = AssetInput(**asset_data)
        
#         if asset_input.is_stream:
#             asset_id = len(listed_assets)
#             listed_assets[asset_id] = {
#                 "owner": wallet_address,
#                 "name": asset_input.name,
#                 "description": asset_input.description,
#                 "price": asset_input.price,
#                 "is_stream": True,
#                 "stream_id": asset_input.data
#             }
#         else:
#             if not file:
#                 raise HTTPException(status_code=400, detail="File is required for static assets")
            
#             # For static assets, we need to store the data first
#             try:
#                 async with aiohttp.ClientSession() as session:
#                     form = aiohttp.FormData()
#                     form.add_field('file', await file.read(), filename=file.filename)
#                     async with session.post(f"{STORE_SERVICE_URL}/store", data=form) as response:
#                         if response.status == 200:
#                             store_result = await response.json()
#                             ipfs_hash = store_result['ipfs_hash']
#                         else:
#                             raise HTTPException(status_code=response.status, detail="Failed to store data")
#             except Exception as e:
#                 error_msg = f"Error storing data: {str(e)}"
#                 logger.error(error_msg)
#                 raise HTTPException(status_code=500, detail=error_msg)
            
#             asset_id = len(listed_assets)
#             listed_assets[asset_id] = {
#                 "owner": wallet_address,
#                 "name": asset_input.name,
#                 "description": asset_input.description,
#                 "price": asset_input.price,
#                 "is_stream": False,
#                 "ipfs_hash": ipfs_hash
#             }
        
#         # Add asset to blockchain
#         try:
#             tx_hash = add_data_asset(contract, str(asset_id), asset_input.price, wallet_address)
#         except Exception as e:
#             error_msg = f"Error adding asset to blockchain: {str(e)}"
#             logger.error(error_msg)
#             raise HTTPException(status_code=500, detail=error_msg)
        
#         logger.info(f"Added asset: {asset_id} by wallet: {wallet_address}")
#         return {"success": True, "asset_id": asset_id, "tx_hash": tx_hash}
#     except HTTPException:
#         raise
#     except Exception as e:
#         error_msg = f"Unexpected error adding asset: {str(e)}"
#         logger.error(error_msg)
#         raise HTTPException(status_code=500, detail=error_msg)

# 3. Asset Purchasing and Stream Subscription
@app.post("/purchase-asset/{asset_id}")
async def purchase_data_asset_endpoint(
    asset_id: int,
    purchase_request: PurchaseRequest,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        logger.info(f"Attempting to purchase asset {asset_id} for wallet {wallet_address}")
        
        # Generate ZKP
        try:
            did = connected_wallets[wallet_address]["did"]
            proof = await generate_zkproof(did, purchase_request.message)
        except Exception as e:
            logger.error(f"Error generating ZKProof: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating proof: {str(e)}")
        
        tx_hash = purchase_data_asset(contract, asset_id, wallet_address, proof)
        logger.info(f"Purchased asset: {asset_id} by wallet: {wallet_address}. TX Hash: {tx_hash}")
        return {"success": True, "tx_hash": tx_hash}
    except Exception as e:
        logger.error(f"Error purchasing asset {asset_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error purchasing asset: {str(e)}")
    

# @app.post("/subscribe-stream")
# async def subscribe_stream_endpoint(
#     subscription: StreamSubscriptionInput,
#     wallet_address: str = Depends(get_authenticated_wallet_address),
#     web3: Web3 = Depends(get_web3)
# ):
#     try:
#         logger.info(f"Attempting to subscribe to stream {subscription.stream_id} for wallet {wallet_address}")
        
#         if not connected_wallets.get(wallet_address, {}).get("authenticated"):
#             logger.warning(f"Wallet {wallet_address} not authenticated")
#             # Authenticate the wallet if it's not already authenticated
#             connected_wallets[wallet_address] = {"authenticated": True}
#             if "did" not in connected_wallets[wallet_address]:
#                 did, key = await did_manager.create_did()
#                 connected_wallets[wallet_address]["did"] = did
#                 connected_wallets[wallet_address]["did_key"] = key

#         did = connected_wallets[wallet_address]["did"]
        
#         # Generate actual proof
#         timestamp = int(time.time())
#         message = f"{wallet_address}:{subscription.stream_id}:{timestamp}"
#         try:
#             proof = await generate_zkproof(did, message)
#         except Exception as e:
#             logger.error(f"Error generating ZKProof: {str(e)}")
#             return JSONResponse(status_code=500, content={"detail": f"Error generating proof: {str(e)}"})
        
#         logger.info(f"Attempting to subscribe to stream service")
#         subscribe_result = await subscribe_stream(subscription.stream_id, did, proof)
#         logger.info(f"Subscribed to stream service. Result: {subscribe_result}")
        
#         return JSONResponse(status_code=200, content={"success": True, "subscription": subscribe_result})
#     except HTTPException as he:
#         logger.error(f"HTTP error subscribing to stream: {str(he)}")
#         return JSONResponse(status_code=he.status_code, content={"detail": str(he.detail)})
#     except Exception as e:
#         logger.error(f"Error subscribing to stream: {str(e)}", exc_info=True)
#         return JSONResponse(status_code=500, content={"detail": f"Error subscribing to stream: {str(e)}"})
    
@app.get("/consumer/access-stream/{asset_id}")
async def access_stream_endpoint(
    asset_id: int,
    wallet_address: str = Depends(get_authenticated_wallet_address),
    contract = Depends(get_contract)
):
    try:
        if asset_id not in listed_assets:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset = listed_assets[asset_id]
        
        if not asset['is_stream']:
            raise HTTPException(status_code=400, detail="This endpoint is for stream assets only")
        
        # Check ownership using the checkOwnership function
        try:
            is_owner = contract.functions.checkOwnership(asset_id, wallet_address).call()
            if not is_owner:
                raise HTTPException(status_code=403, detail="You do not own this asset")
        except ContractLogicError as e:
            logger.error(f"Contract logic error checking ownership: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error checking asset ownership: {str(e)}")
        
        return {"stream_id": asset['stream_id']}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing stream asset: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error accessing stream asset: {str(e)}")

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
        try:
            is_owner = contract.functions.checkOwnership(asset_id, wallet_address).call()
            if not is_owner:
                raise HTTPException(status_code=403, detail="You do not own this asset")
        except ContractLogicError as e:
            logger.error(f"Contract logic error checking ownership: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error checking asset ownership: {str(e)}")
        
        if asset['is_stream']:
            # For streams, return the stream ID
            return {"stream_id": asset['stream_id']}
        else:
            # For static assets, retrieve the data from IPFS
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{STORE_SERVICE_URL}/retrieve", json={"ipfs_hash": asset['ipfs_hash'], "output_path": "temp_file"}) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result['success']:
                                with open("temp_file", "rb") as f:
                                    data = f.read()
                                os.remove("temp_file")  # Clean up the temporary file
                                return {"data": data.decode()}
                            else:
                                raise HTTPException(status_code=500, detail="Failed to retrieve data")
                        else:
                            raise HTTPException(status_code=response.status, detail="Failed to retrieve data")
            except Exception as e:
                logger.error(f"Error retrieving data from IPFS: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error retrieving data: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing asset: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error accessing asset: {str(e)}")



async def subscribe_stream(stream_id: str, did: str, proof: str):
    url = f"{STREAM_SERVICE_URL}/subscribe"
    payload = {
        "streamId": stream_id,
        "did": did,
        "proof": proof,  # Send the proof as a string
        "data": {}  # Add an empty data dict as required by the stream service
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                response_text = await response.text()
                logger.error(f"Failed to subscribe to stream. Status: {response.status}, Response: {response_text}")
                raise HTTPException(status_code=response.status, detail=f"Failed to subscribe to stream: {response_text}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)