import logging
import binascii
from web3.exceptions import ContractLogicError
from web3 import Web3
from config import get_web3_url

logger = logging.getLogger(__name__)

w3 = Web3(Web3.HTTPProvider(get_web3_url()))

def add_data_asset(contract, ipfs_hash: str, price: int, wallet_address: str):
    try:
        if not contract.address:
            raise ValueError(f"Contract address is not set. Contract: {contract}")
        logger.info(f"Adding asset with hash: {ipfs_hash}, price: {price}, from address: {wallet_address}")
        logger.info(f"Contract address: {contract.address}")
        tx_hash = contract.functions.addDataAsset(ipfs_hash, price).transact({'from': wallet_address})
        return tx_hash.hex()
    except Exception as e:
        logger.error(f"Failed to add data asset: {str(e)}")
        raise

def purchase_data_asset(contract, asset_id: int, wallet_address: str, proof: str):
    try:
        # Get the price of the asset from the contract
        asset = contract.functions.dataAssets(asset_id).call()
        asset_price = asset[2]  # Assuming price is the third element in the struct
        
        logger.info(f"Purchasing asset {asset_id} for {asset_price} wei from address: {wallet_address}")
        
        # Get the balance of the wallet
        balance = w3.eth.get_balance(wallet_address)
        logger.info(f"Wallet balance: {balance} wei")

        if balance < asset_price:
            logger.error(f"Insufficient balance. Wallet has {balance} wei, but asset costs {asset_price} wei.")
            raise ValueError("Insufficient balance")

        # Include the price and proof in the transaction
        tx_hash = contract.functions.purchaseDataAsset(asset_id, proof).transact({
            'from': wallet_address,
            'value': asset_price
        })
        
        # Convert the tx_hash to a hexadecimal string
        if isinstance(tx_hash, bytes):
            tx_hash = binascii.hexlify(tx_hash).decode('ascii')
        logger.info(f"Purchase transaction hash: {tx_hash}")
        return tx_hash
    except ContractLogicError as e:
        logger.error(f"Contract logic error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to purchase data asset: {str(e)}")
        raise