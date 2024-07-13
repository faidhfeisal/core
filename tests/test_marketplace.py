import pytest
from web3 import Web3
from eth_account import Account
import os
from src.marketplace import Marketplace
from src.data_management import DataManagementSystem
from src.did_wallet import DIDWallet

@pytest.fixture
def marketplace():
    dms = DataManagementSystem()
    did_wallet = DIDWallet()
    
    # Use Ganache for testing
    web3_provider_uri = "http://127.0.0.1:8545"
    
    # Use the first account from Ganache as the contract owner
    w3 = Web3(Web3.HTTPProvider(web3_provider_uri))
    # contract_owner_address = w3.eth.accounts[0]
    
    # Generate a new private key for testing
    # In a real scenario, you would securely manage and store this key
    contract_owner_private_key = "0x469fa49e991aeb1a1a7acbfe156cc81bab335cccc85f1765b4575d6fc3676c74"

    return Marketplace(dms, did_wallet, web3_provider_uri, contract_owner_private_key)

def test_list_and_buy_asset(marketplace):
    # Use pre-funded Ganache accounts
    seller_address = marketplace.w3.eth.accounts[1]
    buyer_address = marketplace.w3.eth.accounts[2]

    seller_did = f"did:eth:{seller_address}"
    buyer_did = f"did:eth:{buyer_address}"

    # Create an asset
    asset_id = "test_asset"
    marketplace.dms.create_asset(asset_id, seller_did, "Test data")

    # List the asset
    listing = marketplace.list_asset(asset_id, 0.1, seller_did)
    assert listing["asset_id"] == asset_id
    assert listing["price"] == 0.1
    assert listing["seller_did"] == seller_did

    # Buy the asset
    assert marketplace.buy_asset(asset_id, buyer_did)

    # Check access rights
    assert marketplace.get_asset_with_access_check(asset_id, buyer_did).data == "Test data"

def test_access_control(marketplace):
    owner_address = marketplace.w3.eth.accounts[3]
    other_address = marketplace.w3.eth.accounts[4]

    owner_did = f"did:eth:{owner_address}"
    other_did = f"did:eth:{other_address}"

    asset_id = "private_asset"
    marketplace.dms.create_asset(asset_id, owner_did, "Private data")

    # Owner should have access
    assert marketplace.get_asset_with_access_check(asset_id, owner_did).data == "Private data"

    # Other user should not have access
    with pytest.raises(ValueError, match="Access denied"):
        marketplace.get_asset_with_access_check(asset_id, other_did)

def test_get_user_assets(marketplace):
    user_did = marketplace.did_wallet.create_did()
    other_did = marketplace.did_wallet.create_did()

    # Create owned asset
    owned_asset_id = "owned_asset"
    marketplace.dms.create_asset(owned_asset_id, user_did, "Owned data")

    # Create and buy an asset
    bought_asset_id = "bought_asset"
    marketplace.dms.create_asset(bought_asset_id, other_did, "Bought data")
    marketplace.list_asset(bought_asset_id, 5.0, other_did)
    marketplace.buy_asset(bought_asset_id, user_did)

    user_assets = marketplace.get_user_assets(user_did)
    assert len(user_assets) == 2
    assert any(asset["asset_id"] == owned_asset_id for asset in user_assets)
    assert any(asset["asset_id"] == bought_asset_id for asset in user_assets)