import pytest
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from main import app, get_web3, get_contract
from unittest.mock import Mock, AsyncMock
import json
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

@pytest.fixture
def client(mock_web3):
    app.dependency_overrides[get_web3] = lambda: mock_web3
    app.dependency_overrides[get_contract] = lambda: mock_web3.eth.contract.return_value
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
def mock_web3():
    mock = Mock(spec=Web3)
    mock.eth = Mock()
    mock_contract = Mock()
    mock_contract.functions.addDataAsset.return_value.transact.return_value = '74785f68617368'
    mock_contract.functions.purchaseDataAsset.return_value.transact.return_value = '74785f68617368'
    mock_contract.functions.dataAssets.return_value.call.return_value = ["ipfs_hash", "0x123", 100, True]
    mock.eth.contract.return_value = mock_contract
    return mock

@pytest.fixture
def mock_contract(mock_web3):
    contract = mock_web3.eth.contract.return_value
    contract.functions.addDataAsset.return_value.transact.return_value = b'tx_hash'
    return contract

@pytest.fixture
def mock_did_manager(mocker):
    mock = mocker.patch('main.did_manager')
    mock.create_did = AsyncMock()
    mock.resolve_did = AsyncMock()
    mock.verify_did = AsyncMock()
    mock.issue_credential = AsyncMock()
    mock.verify_credential = AsyncMock()
    return mock

@pytest.fixture
def wallet():
    account = Account.create()
    return {"address": account.address, "private_key": account.key}

# Override the get_web3 and get_contract dependencies
app.dependency_overrides[get_web3] = lambda: mock_web3()
app.dependency_overrides[get_contract] = lambda: mock_web3().eth.contract.return_value

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_connect_wallet(client, wallet):
    response = client.post("/connect-wallet", json={"address": wallet["address"]})
    assert response.status_code == 200
    assert response.json()["wallet_address"] == wallet["address"]
    assert "nonce" in response.json()

def test_authenticate_wallet(client, wallet):
    connect_response = client.post("/connect-wallet", json={"address": wallet["address"]})
    nonce = connect_response.json()["nonce"]
    
    message = f"Authenticate to Data Marketplace with nonce: {nonce}"
    message_hash = encode_defunct(text=message)
    signed_message = Account.sign_message(message_hash, wallet["private_key"])
    
    auth_response = client.post("/authenticate-wallet", json={
        "address": wallet["address"],
        "signature": signed_message.signature.hex()
    })
    
    assert auth_response.status_code == 200
    assert auth_response.json()["status"] == "authenticated"

def test_create_did_endpoint(client, wallet, mock_did_manager):
    # Authenticate wallet first
    test_authenticate_wallet(client, wallet)

    mock_did_manager.create_did.return_value = ("did:key:mock", "mock_key")
    response = client.post("/create-did", headers={"wallet-address": wallet["address"]})
    assert response.status_code == 200
    assert response.json() == {"did": "did:key:mock", "key": "mock_key"}

def test_resolve_did_endpoint(client, mock_did_manager):
    mock_did_document = {
        "@context": "https://www.w3.org/ns/did/v1",
        "id": "did:key:mock",
        "verificationMethod": [{
            "id": "did:key:mock#keys-1",
            "type": "Ed25519VerificationKey2018",
            "controller": "did:key:mock",
            "publicKeyBase58": "mock_public_key"
        }]
    }
    mock_did_manager.resolve_did.return_value = mock_did_document
    response = client.get("/resolve-did/did:key:mock")
    assert response.status_code == 200
    assert response.json() == mock_did_document

def test_verify_did_endpoint(client, mock_did_manager):
    mock_did_manager.verify_did.return_value = True
    response = client.post("/verify-did", json={
        "did": "did:key:mock",
        "verification_method": "did:key:mock#keys-1"
    })
    assert response.status_code == 200
    assert response.json() == {"verified": True}

def test_issue_credential_endpoint(client, mock_did_manager):
    mock_signed_credential = json.dumps({
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "issuer": "did:key:mock",
        "issuanceDate": "2023-07-14T00:00:00Z",
        "credentialSubject": {
            "id": "did:example:123",
            "name": "Alice"
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "created": "2023-07-14T00:00:00Z",
            "verificationMethod": "did:key:mock#keys-1",
            "proofPurpose": "assertionMethod",
            "jws": "mock_signature"
        }
    })
    mock_did_manager.issue_credential.return_value = mock_signed_credential

    input_data = {
        "did": "did:key:mock",
        "key": "mock_key",
        "credential": {
            "type": ["VerifiableCredential"],
            "issuer": "did:key:mock",
            "issuanceDate": "2023-07-14T00:00:00Z",
            "credentialSubject": {
                "id": "did:example:123",
                "name": "Alice"
            }
        }
    }
    
    response = client.post("/issue-credential", json=input_data)
    
    print("Response status code:", response.status_code)
    print("Response content:", response.content)
    
    assert response.status_code == 200
    assert "signed_credential" in response.json()

def test_verify_credential_endpoint(client, mock_did_manager):
    mock_did_manager.verify_credential.return_value = True
    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "issuer": "did:key:mock",
        "issuanceDate": "2023-07-14T00:00:00Z",
        "credentialSubject": {
            "id": "did:example:123",
            "name": "Alice"
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "created": "2023-07-14T00:00:00Z",
            "verificationMethod": "did:key:mock#keys-1",
            "proofPurpose": "assertionMethod",
            "jws": "mock_signature"
        }
    }
    
    # Convert the credential to a JSON string
    credential_str = json.dumps(credential)
    
    response = client.post("/verify-credential", json={"credential": credential_str})
    
    print("Response status code:", response.status_code)
    print("Response content:", response.content)
    
    assert response.status_code == 200
    assert response.json() == {"verified": True}

def test_add_asset_endpoint(client, wallet):
    # Authenticate the wallet
    test_authenticate_wallet(client, wallet)

    # Make the request
    response = client.post("/add-asset",
                           headers={"wallet-address": wallet["address"]},
                           json={"ipfs_hash": "https://ipfs.io/ipfs/Qm...", "price": 100})

    # Print debug information
    print("Response status code:", response.status_code)
    print("Response content:", response.content)

    # Assertions
    assert response.status_code == 200
    assert response.json() == {"success": True, "tx_hash": "74785f68617368"}

def test_purchase_asset_endpoint(client, wallet, mock_web3):
    test_authenticate_wallet(client, wallet)

    mock_contract = mock_web3.eth.contract.return_value
    mock_contract.functions.dataAssets.return_value.call.return_value = ["ipfs_hash", "0x123", 100, True]
    mock_contract.functions.purchaseDataAsset.return_value.transact.return_value = '74785f68617368'

    response = client.post("/purchase-asset/1", headers={"wallet-address": wallet["address"]})
    
    print("Response status code:", response.status_code)
    print("Response content:", response.content)

    assert response.status_code == 200
    assert response.json() == {"success": True, "tx_hash": "74785f68617368"}