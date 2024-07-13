from fastapi import APIRouter, HTTPException
from api.models import DIDResponse
from data.did_manager import create_did
from data.data_manager import publish_to_streamr, subscribe_to_streamr
from web3 import Web3

router = APIRouter()

# Set up Web3 connection to local Ganache node
ganache_url = 'http://127.0.0.1:8545'
w3 = Web3(Web3.HTTPProvider(ganache_url))

# Contract ABI and address
contract_abi = [
    {
        "inputs": [
            {"internalType": "string", "name": "ipfsHash", "type": "string"},
            {"internalType": "uint256", "name": "price", "type": "uint256"}
        ],
        "name": "addDataAsset",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "assetId", "type": "uint256"}
        ],
        "name": "purchaseDataAsset",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "dataAssets",
        "outputs": [
            {"internalType": "address payable", "name": "owner", "type": "address"},
            {"internalType": "string", "name": "ipfsHash", "type": "string"},
            {"internalType": "uint256", "name": "price", "type": "uint256"},
            {"internalType": "bool", "name": "forSale", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
contract_address = '0x051be0af150E195D55E490486a38c600976EE6F4'
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

@router.post("/create-did", response_model=DIDResponse)
def create_did_endpoint():
    did, key = create_did()
    return DIDResponse(did=did, key=key)

@router.post("/upload")
def upload_data(file_path: str):
    try:
        ipfs_hash = upload_to_ipfs(file_path)
        return {"success": True, "ipfs_hash": ipfs_hash}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download")
def download_data(ipfs_hash: str, output_path: str):
    try:
        download_from_ipfs(ipfs_hash, output_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-asset")
def add_data_asset(ipfs_hash: str, price: int):
    try:
        # Assume sender address is provided in request headers for simplicity
        sender_address = 'YOUR_WALLET_ADDRESS'
        tx_hash = contract.functions.addDataAsset(ipfs_hash, price).transact({'from': sender_address})
        w3.eth.waitForTransactionReceipt(tx_hash)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/purchase-asset")
def purchase_data_asset(asset_id: int):
    try:
        # Assume sender address is provided in request headers for simplicity
        sender_address = 'YOUR_WALLET_ADDRESS'
        asset = contract.functions.dataAssets(asset_id).call()
        tx_hash = contract.functions.purchaseDataAsset(asset_id).transact({'from': sender_address, 'value': asset[2]})
        w3.eth.waitForTransactionReceipt(tx_hash)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/publish")
def publish_data(stream_id: str, data: dict):
    try:
        publish_to_streamr(stream_id, data)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscribe")
def subscribe_data(stream_id: str):
    try:
        subscription_id = subscribe_to_streamr(stream_id)
        return {"success": True, "subscriptionId": subscription_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
