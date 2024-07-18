# Core Service

## Overview
The Core Service is the main service for DID (Decentralized Identifier) wallet and Marketplace interactions. It serves as the gateway for Data Producers and Data Consumers, interacting with all other microservices in the OwnIt Marketplace.

## Features
- Wallet connection and authentication
- DID creation and management
- Asset management (listing, purchasing, retrieving)
- Revenue withdrawal for data producers

## Setup

### Deploy Smart Contract

Before setting up the Core Service, you need to deploy the `DataMarketplace` smart contract. The contract is located in `core/contracts/DataMarketplace.sol`.

#### Using Hardhat:

1. Install Hardhat:
   ```
   npm install --save-dev hardhat
   ```

2. Initialize a Hardhat project in the `core` directory:
   ```
   npx hardhat init
   ```

3. Copy the `DataMarketplace.sol` contract into the `contracts` directory of your Hardhat project.

4. Create a deployment script in the `scripts` directory, e.g., `deploy.js`:

   ```javascript
   const hre = require("hardhat");

   async function main() {
     const DataMarketplace = await hre.ethers.getContractFactory("DataMarketplace");
     const dataMarketplace = await DataMarketplace.deploy();
     await dataMarketplace.deployed();
     console.log("DataMarketplace deployed to:", dataMarketplace.address);
   }

   main()
     .then(() => process.exit(0))
     .catch((error) => {
       console.error(error);
       process.exit(1);
     });
   ```

5. Start Ganache (make sure it's running on `http://127.0.0.1:8545`).

6. Deploy the contract:
   ```
   npx hardhat run scripts/deploy.js --network localhost
   ```

#### Using Truffle:

1. Install Truffle:
   ```
   npm install -g truffle
   ```

2. Initialize a Truffle project in the `core` directory:
   ```
   truffle init
   ```

3. Copy the `DataMarketplace.sol` contract into the `contracts` directory.

4. Create a migration script in the `migrations` directory, e.g., `2_deploy_contracts.js`:

   ```javascript
   const DataMarketplace = artifacts.require("DataMarketplace");

   module.exports = function(deployer) {
     deployer.deploy(DataMarketplace);
   };
   ```

5. Start Ganache (make sure it's running on `http://127.0.0.1:8545`).

6. Deploy the contract:
   ```
   truffle migrate

### Local Development Setup

1. Clone all service repositories into the same root directory:

   ```bash
   mkdir ownit-marketplace && cd ownit-marketplace
   git clone https://github.com/faidhfeisal/core.git
   git clone https://github.com/faidhfeisal/store.git
   git clone https://github.com/faidhfeisal/stream.git
   ```

2. Set up and start Ganache (local Ethereum blockchain):

   ```bash
   npm install -g ganache-cli
   ganache-cli
   ```

3. Deploy the smart contract (follow the instructions in the "Deploy Smart Contract" section).

4. Set up environment variables for each service (Core, Store, Stream) as described in their respective README files.

5. Install dependencies and start each service:

   For Core and Store (Python services):
   ```bash
   cd <service-directory>
   pip install -r requirements.txt
   python main.py
   ```

   For Stream (Node.js service):
   ```bash
   cd stream
   npm install
   node index.js
   ```

#### Docker Setup

1. Clone all service repositories into the same root directory as in the local setup.

2. Create a `.env` file in the root directory with all the necessary environment variables:

   ```
   CONTRACT_ADDRESS=<deployed_contract_address>
   CONTRACT_ABI=<contract_abi_json_string>
   PRODUCER_PRIVATE_KEY=<producer_private_key>
   PRODUCER_WALLET_ADDRESS=<producer_wallet_address>
   CONSUMER_WALLET_ADDRESS=<consumer_wallet_address>
   CONSUMER_PRIVATE_KEY=<consumer_private_key>
   PINATA_API_URL=<pinata_api_url>
   PINATA_API_KEY=<pinata_api_key>
   PINATA_SECRET_API_KEY=<pinata_secret_api_key>
   STREAMR_PRIVATE_KEY=<streamr_private_key>
   ENCRYPTION_SECRET=<encryption_secret>
   ```

3. Build and start the services using Docker Compose:

   Copy the 

   ```bash
   cp docker-compose.yaml ../ && cd ../ && docker-compose up --build


   ```

   This will start Ganache, Core, Store, and Stream services.

4. Deploy the smart contract to the Ganache instance running in Docker:

   ```bash
   docker exec -it ownit-ai-data-layer2_core_1 npx hardhat run scripts/deploy.js --network localhost
   ```

   Update the `CONTRACT_ADDRESS` in the `.env` file with the deployed contract address.

5. Restart the services to pick up the new contract address:

   ```bash
   docker-compose down
   docker-compose up
   ```

### API Endpoints

All services have a postman collection at the root of the directory which documents all endpoints

## Running the Demo Script

For local setup:
```bash
python client_demo.py --producer-address <producer_wallet_address> --producer-key <producer_private_key> --consumer-address <consumer_wallet_address> --consumer-key <consumer_private_key>
```

For Docker setup:
```bash
docker exec -it ownit-ai-data-layer2_core_1 python client_demo.py --producer-address <producer_wallet_address> --producer-key <producer_private_key> --consumer-address <consumer_wallet_address> --consumer-key <consumer_private_key>
```


## Security Considerations
- Ensure proper key management for wallet private keys
- Implement rate limiting and additional authentication for sensitive endpoints
- Regularly update dependencies and audit the codebase for vulnerabilities
- In a production environment, use a secure method to manage and inject the contract ABI and address
- Do not use the same accounts or private keys used in development for any production or mainnet deployments
- Ensure that the communication between services is secure, especially in a production environment
- When using Docker, be cautious about exposing ports and manage environment variables securely
