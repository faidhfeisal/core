import pytest
import json
import sys
from core.did_manager import create_did, resolve_did, verify_did, issue_credential, verify_credential
from unittest.mock import Mock, AsyncMock, MagicMock
from didkit import DIDKitException

pytestmark = pytest.mark.asyncio
sys.modules['didkit'] = MagicMock()

@pytest.fixture
def mock_didkit():
    mock = Mock()
    mock.generate_ed25519_key.return_value = "mock_key"
    mock.key_to_did.return_value = "did:key:mock"
    mock.resolve_did.return_value = json.dumps({
        "id": "did:key:mock",
        "verificationMethod": [{"id": "did:key:mock#key-1"}]
    })
    mock.verify.return_value = json.dumps({"verified": True})
    mock.verify_credential.return_value = json.dumps({"verified": True})
    mock.key_to_verification_method.return_value = "did:key:mock#key-1"
    mock.issue_credential.return_value = json.dumps({
        "proof": {
            "type": "Ed25519Signature2018",
            "created": "2023-07-14T00:00:00Z",
            "verificationMethod": "did:key:mock#key-1",
            "proofPurpose": "assertionMethod",
            "jws": "mock_jws"
        }
    })
    mock.DIDKitException = Exception
    return mock

@pytest.mark.asyncio
async def test_create_did(mock_didkit, mocker):
    mocker.patch('core.did_manager.didkit', mock_didkit)
    did, key = await create_did()
    assert did == "did:key:mock"
    assert key == "mock_key"
    mock_didkit.generate_ed25519_key.assert_called_once()
    mock_didkit.key_to_did.assert_called_once_with("key", "mock_key")

@pytest.mark.asyncio
async def test_resolve_did(mock_didkit, mocker):
    mocker.patch('core.did_manager.didkit', mock_didkit)
    result = await resolve_did("did:key:mock")
    assert result == {
        "id": "did:key:mock",
        "verificationMethod": [{"id": "did:key:mock#key-1"}]
    }

@pytest.mark.asyncio
async def test_verify_did(mock_didkit, mocker):
    mocker.patch('core.did_manager.didkit', mock_didkit)
    result = await verify_did("did:key:mock", "did:key:mock#key-1")
    assert result is True

@pytest.mark.asyncio
async def test_issue_credential(mock_didkit, mocker):
    mocker.patch('core.did_manager.didkit', mock_didkit)
    credential = {
        "type": ["VerifiableCredential"],
        "issuer": "did:key:mock",
        "issuanceDate": "2023-07-14T00:00:00Z",
        "credentialSubject": {
            "id": "did:example:123",
            "name": "Alice"
        }
    }
    result = await issue_credential("did:key:mock", "mock_key", credential)
    assert json.loads(result)["proof"]["verificationMethod"] == "did:key:mock#key-1"

@pytest.mark.asyncio
async def test_verify_credential(mock_didkit, mocker):
    mocker.patch('core.did_manager.didkit', mock_didkit)
    credential = json.dumps({
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential"],
        "issuer": "did:key:mock",
        "issuanceDate": "2023-07-14T00:00:00Z",
        "credentialSubject": {
            "id": "did:example:123",
            "name": "Alice"
        }
    })
    result = await verify_credential(credential)
    assert result == True