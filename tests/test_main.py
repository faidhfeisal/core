import pytest
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from main import app, web3
from unittest.mock import Mock, patch
import json

client = TestClient(app)

@pytest.fixture
def mock_web3(monkeypatch):
    mock = Mock(spec=Web3)
    mock.eth = Mock()
    mock.eth.contract.return_value = Mock()
    mock.eth.contract.return_value.functions.addDataAsset.return_value.transact.return_value = b'tx_hash'
    mock.eth.contract.return_value.functions.purchaseDataAsset.return_value.transact.return_value = b'tx_hash'
    monkeypatch.setattr("main.web3", mock)
    return mock

@pytest.fixture
def wallet():
    account = Account.create()
    return {"address": account.address, "private_key": account.key}

@pytest.fixture
def authenticated_wallet(wallet):
    response = client.post("/connect-wallet", json={"address": wallet["address"]})
    nonce = response.json()["nonce"]
    message = f"Authenticate to Data Marketplace with nonce: {nonce}"
    signed_message = Account.sign_message(encode_defunct(text=message), wallet["private_key"])
    client.post("/authenticate-wallet", json={
        "address": wallet["address"],
        "signature": signed_message.signature.hex()
    })
    return wallet

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_connect_wallet(wallet):
    response = client.post("/connect-wallet", json={"address": wallet["address"]})
    assert response.status_code == 200
    assert response.json()["wallet_address"] == wallet["address"]
    assert "nonce" in response.json()

def test_authenticate_wallet(wallet):
    connect_response = client.post("/connect-wallet", json={"address": wallet["address"]})
    nonce = connect_response.json()["nonce"]
    message = f"Authenticate to Data Marketplace with nonce: {nonce}"
    signed_message = Account.sign_message(encode_defunct(text=message), wallet["private_key"])
    auth_response = client.post("/authenticate-wallet", json={
        "address": wallet["address"],
        "signature": signed_message.signature.hex()
    })
    assert auth_response.status_code == 200
    assert auth_response.json()["status"] == "authenticated"

@patch("main.did_manager.create_did")
def test_create_did(mock_create_did, authenticated_wallet):
    mock_create_did.return_value = ("did:example:123", "mock_key")
    response = client.post("/create-did", headers={"wallet-address": authenticated_wallet["address"]})
    assert response.status_code == 200
    assert response.json() == {"did": "did:example:123", "key": "mock_key"}

@patch("main.store_data")
@patch("main.add_data_asset")
def test_add_static_asset(mock_add_data_asset, mock_store_data, authenticated_wallet, mock_web3):
    mock_store_data.return_value = {"ipfs_hash": "Qm..."}
    mock_add_data_asset.return_value = "0x..."
    asset_data = {
        "name": "Test Asset",
        "description": "A test asset",
        "price": 100,
        "is_stream": False,
        "data": "test_file_path"
    }
    response = client.post("/add-asset", json=asset_data, headers={"wallet-address": authenticated_wallet["address"]})
    assert response.status_code == 200
    assert "asset_id" in response.json()
    assert response.json()["success"] is True

@patch("main.add_data_asset")
def test_add_stream_asset(mock_add_data_asset, authenticated_wallet, mock_web3):
    mock_add_data_asset.return_value = "0x..."
    asset_data = {
        "name": "Test Stream",
        "description": "A test stream",
        "price": 100,
        "is_stream": True,
        "data": "stream_id_123"
    }
    response = client.post("/add-asset", json=asset_data, headers={"wallet-address": authenticated_wallet["address"]})
    assert response.status_code == 200
    assert "asset_id" in response.json()
    assert response.json()["success"] is True

@patch("main.store_data")
@patch("main.add_data_asset")
def test_purchase_asset(mock_add_data_asset, mock_store_data, authenticated_wallet, mock_web3):
    # Mock the store_data function
    mock_store_data.return_value = {"ipfs_hash": "Qm..."}
    
    # Mock the add_data_asset function
    mock_add_data_asset.return_value = "0x..."

    # First, add an asset
    asset_data = {
        "name": "Test Asset",
        "description": "A test asset",
        "price": 100,
        "is_stream": False,
        "data": "test_file_path"
    }
    add_response = client.post("/add-asset", json=asset_data, headers={"wallet-address": authenticated_wallet["address"]})
    assert add_response.status_code == 200
    assert "asset_id" in add_response.json()
    asset_id = add_response.json()["asset_id"]

    # Now purchase the asset
    purchase_data = {"asset_id": asset_id}
    response = client.post("/purchase-asset", json=purchase_data, headers={"wallet-address": authenticated_wallet["address"]})
    assert response.status_code == 200
    assert response.json()["success"] is True

@patch("main.subscribe_stream")
@patch("main.purchase_data_asset")
@patch("main.add_data_asset")
@patch("main.did_manager.create_did")
def test_subscribe_stream(mock_create_did, mock_add_data_asset, mock_purchase_data_asset, mock_subscribe_stream, authenticated_wallet, mock_web3):
    # Mock the create_did function
    mock_create_did.return_value = ("did:example:123", "mock_key")

    # Mock the add_data_asset function
    mock_add_data_asset.return_value = "0x..."

    # Authenticate the wallet
    nonce = client.post("/connect-wallet", json={"address": authenticated_wallet["address"]}).json()["nonce"]
    message = f"Authenticate to Data Marketplace with nonce: {nonce}"
    signed_message = Account.sign_message(encode_defunct(text=message), authenticated_wallet["private_key"])
    auth_response = client.post("/authenticate-wallet", json={
        "address": authenticated_wallet["address"],
        "signature": signed_message.signature.hex()
    })
    assert auth_response.status_code == 200

    # First, add a stream asset
    asset_data = {
        "name": "Test Stream",
        "description": "A test stream",
        "price": 100,
        "is_stream": True,
        "data": "stream_id_123"
    }
    add_response = client.post("/add-asset", json=asset_data, headers={"wallet-address": authenticated_wallet["address"]})
    assert add_response.status_code == 200

    # Mock the purchase_data_asset function
    mock_purchase_data_asset.return_value = "0x..."

    # Mock the subscribe_stream function
    mock_subscribe_stream.return_value = {"subscription": "success"}

    subscription_data = {"stream_id": "stream_id_123"}
    response = client.post("/subscribe-stream", json=subscription_data, headers={"wallet-address": authenticated_wallet["address"]})

    # Print response content for debugging
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "subscription" in response.json()

@patch("main.retrieve_data")
@patch("main.store_data")
@patch("main.add_data_asset")
def test_access_static_asset(mock_add_data_asset, mock_store_data, mock_retrieve_data, authenticated_wallet, mock_web3):
    # Mock the store_data function
    mock_store_data.return_value = {"ipfs_hash": "Qm..."}
    
    # Mock the add_data_asset function
    mock_add_data_asset.return_value = "0x..."

    # First, add and purchase an asset
    asset_data = {
        "name": "Test Asset",
        "description": "A test asset",
        "price": 100,
        "is_stream": False,
        "data": "test_file_path"
    }
    add_response = client.post("/add-asset", json=asset_data, headers={"wallet-address": authenticated_wallet["address"]})
    assert add_response.status_code == 200
    assert "asset_id" in add_response.json(), f"Response: {add_response.json()}"
    asset_id = add_response.json()["asset_id"]
    client.post("/purchase-asset", json={"asset_id": asset_id}, headers={"wallet-address": authenticated_wallet["address"]})

    mock_retrieve_data.return_value = {"data": "test_data"}
    response = client.get(f"/access-asset/{asset_id}", headers={"wallet-address": authenticated_wallet["address"]})
    assert response.status_code == 200
    assert "data" in response.json()

def test_access_stream_asset(authenticated_wallet, mock_web3):
    # First, add a stream asset
    asset_data = {
        "name": "Test Stream",
        "description": "A test stream",
        "price": 100,
        "is_stream": True,
        "data": "stream_id_123"
    }
    add_response = client.post("/add-asset", json=asset_data, headers={"wallet-address": authenticated_wallet["address"]})
    asset_id = add_response.json()["asset_id"]

    response = client.get(f"/access-asset/{asset_id}", headers={"wallet-address": authenticated_wallet["address"]})
    assert response.status_code == 200
    assert response.json()["stream_id"] == "stream_id_123"