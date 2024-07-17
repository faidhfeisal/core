import logging
import binascii
from web3.exceptions import ContractLogicError
from web3 import Web3
from config import get_web3_url, WALLET_PRIVATE_KEY

logger = logging.getLogger(__name__)

web3 = Web3(Web3.HTTPProvider(get_web3_url()))

def add_data_asset(contract, ipfs_hash: str, price: int, wallet_address: str):
    try:
        # Ensure the wallet_address is checksum address
        checksum_address = Web3.to_checksum_address(wallet_address)
        
        # Get the nonce for the transaction
        nonce = web3.eth.get_transaction_count(checksum_address)
        
        # Build the transaction
        txn = contract.functions.addDataAsset(ipfs_hash, price).build_transaction({
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
        
        # Wait for the transaction receipt
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt['status'] == 0:
            raise Exception("Transaction failed")
        
        # Get the asset ID from the event logs
        logs = contract.events.DataAssetAdded().process_receipt(tx_receipt)
        if logs:
            asset_id = logs[0]['args']['assetId']
        else:
            raise Exception("Failed to get asset ID from event logs")
        
        logger.info(f"Asset added to blockchain. Asset ID: {asset_id}, Owner: {checksum_address}")
        return asset_id, tx_hash.hex()
    except Exception as e:
        logger.error(f"Error adding asset to blockchain: {str(e)}")
        raise

def purchase_data_asset(contract, asset_id: int, wallet_address: str, proof: str):
    try:
        # Get the price of the asset from the contract
        asset = contract.functions.dataAssets(asset_id).call()
        asset_price = asset[2]  # Assuming price is the third element in the struct
        
        logger.info(f"Purchasing asset {asset_id} for {asset_price} wei from address: {wallet_address}")
        
        # Get the balance of the wallet
        balance = web3.eth.get_balance(wallet_address)
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