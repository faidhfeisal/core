// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DataMarketplace {
    struct DataAsset {
        address payable owner;
        string ipfsHash;
        uint256 price;
        bool forSale;
    }

    mapping(uint256 => DataAsset) public dataAssets;
    uint256 public nextAssetId;

    event DataAssetAdded(uint256 assetId, address owner, string ipfsHash, uint256 price);
    event DataAssetPurchased(uint256 assetId, address buyer);
    event DataAssetRemoved(uint256 assetId, address owner);
    event Debug(string message, uint256 value);
    event RevenueUpdated(address owner, uint256 amount);

    mapping(address => uint256) public pendingRevenue;

    function addDataAsset(string memory ipfsHash, uint256 price) public {
        emit Debug("Before adding asset", nextAssetId);
        dataAssets[nextAssetId] = DataAsset(payable(msg.sender), ipfsHash, price, true);
        emit DataAssetAdded(nextAssetId, msg.sender, ipfsHash, price);
        emit Debug("After adding asset", nextAssetId);
        nextAssetId++;
        emit Debug("After incrementing nextAssetId", nextAssetId);
    }

    function purchaseDataAsset(uint256 assetId, string memory proof) public payable {
        require(verifyProof(proof), "Invalid proof");
        DataAsset storage asset = dataAssets[assetId];
        require(asset.forSale, "Asset not for sale");
        require(msg.value >= asset.price, "Insufficient payment");

        address payable previousOwner = asset.owner;
        uint256 payment = msg.value;

        asset.owner = payable(msg.sender);
        asset.forSale = false;

        // Update pending revenue instead of immediate transfer
        pendingRevenue[previousOwner] += payment;
        emit RevenueUpdated(previousOwner, pendingRevenue[previousOwner]);

        emit DataAssetPurchased(assetId, msg.sender);
    }

    function withdrawRevenue() public {
        uint256 amount = pendingRevenue[msg.sender];
        require(amount > 0, "No revenue to withdraw");

        pendingRevenue[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
        emit RevenueUpdated(msg.sender, 0);
    }

    function removeAsset(uint256 assetId) public {
        require(assetId < nextAssetId, "Asset does not exist");
        DataAsset storage asset = dataAssets[assetId];
        require(msg.sender == asset.owner, string(abi.encodePacked("Only the owner can remove the asset. Caller: ", addressToString(msg.sender), ", Owner: ", addressToString(asset.owner))));

        delete dataAssets[assetId];
        emit DataAssetRemoved(assetId, msg.sender);
    }

    function checkOwnership(uint256 assetId, address user) public view returns (bool) {
        require(assetId < nextAssetId, "Asset does not exist");
        DataAsset storage asset = dataAssets[assetId];
        return asset.owner == user;
    }

    function getAssetOwner(uint256 assetId) public view returns (address) {
        require(assetId < nextAssetId, "Asset does not exist");
        return dataAssets[assetId].owner;
    }

    function addressToString(address _addr) internal pure returns(string memory) {
        bytes32 value = bytes32(uint256(uint160(_addr)));
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(42);
        str[0] = '0';
        str[1] = 'x';
        for (uint256 i = 0; i < 20; i++) {
            str[2+i*2] = alphabet[uint8(value[i + 12] >> 4)];
            str[3+i*2] = alphabet[uint8(value[i + 12] & 0x0f)];
        }
        return string(str);
    }

    function verifyProof(string memory proof) public pure returns (bool) {
        // In a real implementation, this would contain complex ZKP verification logic
        // For this PoC, we'll just check if the proof is not empty
        return bytes(proof).length > 0;
    }
}