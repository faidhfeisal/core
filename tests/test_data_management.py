import pytest
from src.data_management import DataManagementSystem

def test_data_management_system():
    dms = DataManagementSystem()

    # Test create_asset
    asset = dms.create_asset("asset1", "did:eth:owner1", "Test data")
    assert asset.asset_id == "asset1"
    assert asset.owner_did == "did:eth:owner1"
    assert asset.data == "Test data"

    # Test get_asset
    retrieved_asset = dms.get_asset("asset1")
    assert retrieved_asset.asset_id == "asset1"
    assert retrieved_asset.owner_did == "did:eth:owner1"
    assert retrieved_asset.data == "Test data"

    # Test update_asset
    updated_asset = dms.update_asset("asset1", "Updated data")
    assert updated_asset.data == "Updated data"

    # Test list_assets
    assets_list = dms.list_assets()
    assert len(assets_list) == 1
    assert assets_list[0]["asset_id"] == "asset1"

    # Test delete_asset
    dms.delete_asset("asset1")
    with pytest.raises(ValueError):
        dms.get_asset("asset1")

    # Test stream data
    stream_asset = dms.create_asset("stream1", "did:eth:owner2", [], is_stream=True)
    dms.append_stream_data("stream1", "Stream data 1")
    dms.append_stream_data("stream1", "Stream data 2")
    assert dms.get_asset("stream1").data == ["Stream data 1", "Stream data 2"]

    # Test encrypted data
    dms = DataManagementSystem()
    password = "secret_password"
    encrypted_asset = dms.create_asset("encrypted1", "did:eth:owner3", {"sensitive": "data"}, encrypt=True, password=password)
    assert encrypted_asset.is_encrypted
    
    # Try to get asset without decryption
    retrieved_asset = dms.get_asset("encrypted1")
    assert isinstance(retrieved_asset.data, str)  # Still encrypted
    
    # Get and decrypt asset
    decrypted_asset = dms.get_asset("encrypted1", decrypt=True, password=password)
    assert decrypted_asset.data == {"sensitive": "data"}

    # Test wrong password
    with pytest.raises(Exception):  # The exact exception might depend on the encryption library
        dms.get_asset("encrypted1", decrypt=True, password="wrong_password")

def test_data_management_errors():
    dms = DataManagementSystem()

    # Test creating duplicate asset
    dms.create_asset("asset1", "did:eth:owner1", "Test data")
    with pytest.raises(ValueError):
        dms.create_asset("asset1", "did:eth:owner1", "Duplicate data")

    # Test getting non-existent asset
    with pytest.raises(ValueError):
        dms.get_asset("non_existent_asset")

    # Test updating non-existent asset
    with pytest.raises(ValueError):
        dms.update_asset("non_existent_asset", "Updated data")

    # Test deleting non-existent asset
    with pytest.raises(ValueError):
        dms.delete_asset("non_existent_asset")

    # Test appending to non-stream asset
    dms.create_asset("static_asset", "did:eth:owner1", "Static data")
    with pytest.raises(ValueError):
        dms.append_stream_data("static_asset", "Stream data")

def test_encrypted_stream_data():
    dms = DataManagementSystem()
    password = "stream_password"
    
    stream_asset = dms.create_asset("stream2", "did:eth:owner4", [], is_stream=True, encrypt=True, password=password)
    dms.append_stream_data("stream2", "Stream data 1", password=password)
    dms.append_stream_data("stream2", "Stream data 2", password=password)
    
    decrypted_asset = dms.get_asset("stream2", decrypt=True, password=password)
    assert len(decrypted_asset.data) == 2
    assert "Stream data 1" in decrypted_asset.data
    assert "Stream data 2" in decrypted_asset.data