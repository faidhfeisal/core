import pytest
from src.did_wallet import DIDWallet, DataOwnership

def test_did_creation_and_signature():
    wallet = DIDWallet()
    did = wallet.create_did()
    
    message = "Hello, World!"
    signed_message = wallet.sign_message(did, message)
    
    assert wallet.verify_signature(message, signed_message.signature, did)

def test_data_ownership():
    wallet = DIDWallet()
    ownership = DataOwnership(wallet)
    
    owner_did = wallet.create_did()
    asset_id = "asset1"
    data = "Some valuable data"
    
    asset = ownership.create_asset(owner_did, asset_id, data)
    assert ownership.verify_ownership(owner_did, asset_id)
    
    new_owner_did = wallet.create_did()
    transfer_message = f"Transfer asset {asset_id} to {new_owner_did}"
    signed_message = wallet.sign_message(owner_did, transfer_message)
    
    ownership.transfer_ownership(owner_did, new_owner_did, asset_id, signed_message.signature)
    assert ownership.verify_ownership(new_owner_did, asset_id)
    assert not ownership.verify_ownership(owner_did, asset_id)