import pytest
from unittest.mock import Mock
from core.marketplace import add_data_asset, purchase_data_asset

@pytest.fixture
def mock_contract():
    contract = Mock()
    contract.functions.addDataAsset.return_value.transact.return_value = '74785f68617368'
    contract.functions.dataAssets.return_value.call.return_value = ["ipfs_hash", "0x123", 100, True]
    contract.functions.purchaseDataAsset.return_value.transact.return_value = '74785f68617368'
    return contract

def test_add_data_asset(mock_contract):
    result = add_data_asset(mock_contract, "ipfs_hash", 100, "0x123")

    assert result == '74785f68617368'
    mock_contract.functions.addDataAsset.assert_called_once_with("ipfs_hash", 100)
    mock_contract.functions.addDataAsset.return_value.transact.assert_called_once_with({'from': '0x123'})

def test_purchase_data_asset(mock_contract):
    result = purchase_data_asset(mock_contract, 1, "0x456")

    assert result == '74785f68617368'
    mock_contract.functions.purchaseDataAsset.assert_called_once_with(1)
    mock_contract.functions.purchaseDataAsset.return_value.transact.assert_called_once_with({'from': '0x456'})