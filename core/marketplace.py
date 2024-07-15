import logging
import binascii

logger = logging.getLogger(__name__)

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

def purchase_data_asset(contract, asset_id: int, wallet_address: str):
    try:
        tx_hash = contract.functions.purchaseDataAsset(asset_id).transact({'from': wallet_address})
        # Convert the tx_hash to a hexadecimal string
        if isinstance(tx_hash, bytes):
            tx_hash = binascii.hexlify(tx_hash).decode('ascii')
        return tx_hash
    except Exception as e:
        logger.error(f"Failed to purchase data asset: {str(e)}")
        raise