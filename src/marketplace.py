import logging
import binascii
from web3.exceptions import ContractLogicError
from web3 import Web3
from config import get_web3_url, PRODUCER_PRIVATE_KEY, CONSUMER_PRIVATE_KEY, CONSUMER_WALLET_ADDRESS, PRODUCER_WALLET_ADDRESS

logger = logging.getLogger(__name__)

web3 = Web3(Web3.HTTPProvider(get_web3_url()))

def get_private_key(wallet_address):
    if wallet_address.lower() == PRODUCER_WALLET_ADDRESS.lower():
        return PRODUCER_PRIVATE_KEY
    elif wallet_address.lower() == CONSUMER_WALLET_ADDRESS.lower():
        return CONSUMER_PRIVATE_KEY
    else:
        raise ValueError(f"No private key found for address {wallet_address}")

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
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRODUCER_PRIVATE_KEY)
        
        # Send the transaction
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for the transaction receipt
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt['status'] == 0:
            raise Exception("Transaction failed")
        
        logger.info(f"Transaction hash: {tx_hash.hex()}")
        logger.info(f"Transaction receipt: {tx_receipt}")
        
        # Get the asset ID from the event logs
        logs = contract.events.DataAssetAdded().process_receipt(tx_receipt)
        logger.debug(f"Logs from process_receipt: {logs}")
        if logs:
            asset_id = logs[0]['args']['assetId']
            logger.info(f"Asset added to blockchain. Asset ID: {asset_id}, Owner: {checksum_address}")
            return asset_id, tx_hash.hex()
        else:
            logger.error("Failed to get asset ID from event logs")
            logger.debug(f"Transaction receipt: {tx_receipt}")
            raise Exception("Failed to get asset ID from event logs")
    except Exception as e:
        logger.error(f"Error adding asset to blockchain: {str(e)}")
        raise

def purchase_data_asset(contract, asset_id: int, wallet_address: str, price: int, proof: str):
    try:
        # Ensure the wallet_address is checksum address
        checksum_address = Web3.to_checksum_address(wallet_address)
        
        # Get the nonce for the transaction
        nonce = web3.eth.get_transaction_count(checksum_address)
        
        # Build the transaction
        txn = contract.functions.purchaseDataAsset(asset_id, proof).build_transaction({
            'chainId': web3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': web3.eth.gas_price,
            'nonce': nonce,
            'from': checksum_address,
            'value': price
        })


        
        # Sign the transaction
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=CONSUMER_PRIVATE_KEY)
        
        # Send the transaction
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for the transaction receipt
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        if tx_receipt['status'] == 0:
            raise Exception("Transaction failed")
        
        logger.info(f"Transaction hash: {tx_hash.hex()}")
        logger.info(f"Transaction receipt: {tx_receipt}")
        
        if tx_receipt['status'] == 0:
            raise Exception("Transaction failed")
        
        logger.info(f"Asset {asset_id} purchased by {checksum_address}")
        return tx_hash.hex()
    except ContractLogicError as e:
        logger.error(f"Contract logic error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to purchase data asset: {str(e)}")
        raise



def withdraw_revenue(contract, wallet_address: str):
    try:
        # Ensure the wallet_address is checksum address
        checksum_address = Web3.to_checksum_address(wallet_address)
        
        # Get the pending revenue for the address
        pending_revenue = contract.functions.pendingRevenue(checksum_address).call()
        
        if pending_revenue == 0:
            logger.info(f"No revenue to withdraw for address: {checksum_address}")
            return None
        
        # Get the correct private key for this wallet address
        private_key = get_private_key(checksum_address)
        
        # Get the nonce for the transaction
        nonce = web3.eth.get_transaction_count(checksum_address)
        
        # Build the transaction
        txn = contract.functions.withdrawRevenue().build_transaction({
            'chainId': web3.eth.chain_id,
            'gas': 2000000,
            'gasPrice': web3.eth.gas_price,
            'nonce': nonce,
            'from': checksum_address
        })
        
        # Sign the transaction with the correct private key
        signed_txn = web3.eth.account.sign_transaction(txn, private_key=private_key)
        
        # Send the transaction
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for the transaction receipt
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt['status'] == 0:
            raise Exception("Transaction failed")
        
        logger.info(f"Revenue withdrawn by {checksum_address}")
        return tx_hash.hex()
    except ContractLogicError as e:
        logger.error(f"Contract logic error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to withdraw revenue: {str(e)}")