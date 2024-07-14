import logging

logger = logging.getLogger(__name__)

def add_data_asset(contract, ipfs_hash: str, price: int, wallet_address: str):
    try:
        tx_hash = contract.functions.addDataAsset(ipfs_hash, price).transact({'from': wallet_address})
        return tx_hash  # Return the tx_hash as is, without any additional encoding
    except Exception as e:
        logger.error(f"Failed to add data asset: {str(e)}")
        raise

def purchase_data_asset(contract, asset_id: int, wallet_address: str):
    try:
        tx_hash = contract.functions.purchaseDataAsset(asset_id).transact({'from': wallet_address})
        return tx_hash  # Return the tx_hash as is, without any additional encoding
    except Exception as e:
        logger.error(f"Failed to purchase data asset: {str(e)}")
        raise