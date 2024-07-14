import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from pydantic import BaseModel, HttpUrl
import logging
import secrets
from typing import Dict, Any
from core import did_manager
from core.marketplace import add_data_asset, purchase_data_asset

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
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

# Web3 setup
def get_web3():
    return Web3(Web3.HTTPProvider(GANACHE_URL))

def get_contract(w3: Web3 = Depends(get_web3)):
    contract_abi = [ ... ]  # Contract ABI
    return w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)


# Simple in-memory wallet store
connected_wallets = {}

class WalletConnect(BaseModel):
    address: str

class WalletAuth(BaseModel):
    address: str
    signature: str

class AssetInput(BaseModel):
    ipfs_hash: HttpUrl
    price: int

class DidVerificationInput(BaseModel):
    did: str
    verification_method: str

class CredentialInput(BaseModel):
    credential: str

class CredentialIssueInput(BaseModel):
    did: str
    key: str
    credential: Dict[str, Any]

def get_wallet_address(wallet_address: str = Header(...)):
    if wallet_address not in connected_wallets:
        raise HTTPException(status_code=401, detail="Wallet not connected")
    return wallet_address

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/connect-wallet")
async def connect_wallet(wallet: WalletConnect):
    if not Web3.is_address(wallet.address):
        raise HTTPException(status_code=400, detail="Invalid wallet address")
    
    # Generate a nonce for this wallet
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
        recovered_address = Account.recover_message(message_hash, signature=wallet_auth.signature)
        if recovered_address.lower() != wallet_auth.address.lower():
            raise ValueError("Invalid signature")
        connected_wallets[wallet_auth.address]["authenticated"] = True
        return {"status": "authenticated", "wallet_address": wallet_auth.address}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.post("/create-did")
async def create_did_endpoint(wallet_address: str = Depends(get_wallet_address)):
    try:
        did, key = await did_manager.create_did()
        logger.info(f"Created DID: {did} for wallet: {wallet_address}")
        return {"did": did, "key": key}
    except Exception as e:
        logger.error(f"Error creating DID: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resolve-did/{did}")
async def resolve_did_endpoint(did: str):
    try:
        did_document = await did_manager.resolve_did(did)
        return did_document
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-did")
async def verify_did_endpoint(input: DidVerificationInput):
    result = await did_manager.verify_did(input.did, input.verification_method)
    return {"verified": result}

@app.post("/issue-credential")
async def issue_credential_endpoint(input: CredentialIssueInput):
    try:
        signed_credential = await did_manager.issue_credential(input.did, input.key, input.credential)
        return {"signed_credential": signed_credential}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-credential")
async def verify_credential_endpoint(input: CredentialInput):
    result = await did_manager.verify_credential(input.credential)
    return {"verified": result}

@app.post("/add-asset")
async def add_data_asset_endpoint(
    asset: AssetInput,
    wallet_address: str = Depends(get_wallet_address),
    contract = Depends(get_contract)
):
    try:
        tx_hash = add_data_asset(contract, str(asset.ipfs_hash), asset.price, wallet_address)
        logger.info(f"Added asset: {asset.ipfs_hash} by wallet: {wallet_address}")
        return {"success": True, "tx_hash": tx_hash}
    except Exception as e:
        logger.error(f"Error adding asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Error adding asset")

@app.post("/purchase-asset/{asset_id}")
async def purchase_data_asset_endpoint(
    asset_id: int,
    wallet_address: str = Depends(get_wallet_address),
    contract = Depends(get_contract)
):
    try:
        tx_hash = purchase_data_asset(contract, asset_id, wallet_address)
        logger.info(f"Purchased asset: {asset_id} by wallet: {wallet_address}")
        return {"success": True, "tx_hash": tx_hash}
    except Exception as e:
        logger.error(f"Error purchasing asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Error purchasing asset")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)