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

### Docker Setup

1. Clone all service repositories into the same root directory:

   ```bash
   mkdir ownit-marketplace && cd ownit-marketplace
   git clone https://github.com/faidhfeisal/core.git
   git clone https://github.com/faidhfeisal/store.git
   git clone https://github.com/faidhfeisal/stream.git
   ```

2. Create a `.env` file in the root directory with all the necessary environment variables:

   ```
   NETWORK_URL=http://ganache:8545
   CONTRACT_ADDRESS=<will_be_updated_after_deployment>
   CONTRACT_ABI=<contract_abi_json_string>
   PRODUCER_PRIVATE_KEY=<producer_private_key>
   PRODUCER_WALLET_ADDRESS=<producer_wallet_address>
   CONSUMER_WALLET_ADDRESS=<consumer_wallet_address>
   CONSUMER_PRIVATE_KEY=<consumer_private_key>
   PINATA_API_URL=<pinata_api_url>
   PINATA_API_KEY=<pinata_api_key>
   PINATA_SECRET_API_KEY=<pinata_secret_api_key>
   STREAMR_PRIVATE_KEY=<streamr_private_key> //make sure this key is in single quotes
   ENCRYPTION_SECRET=<encryption_secret>
   ```

3. Build and start the services using Docker Compose:

   Copy the docker-compose.yml to the root directory where the .env file is and run:

   ```bash
   docker-compose up -d --build
   ```

   This will start Ganache, deploy the smart contract, and then start the Core, Store, and Stream services.

4. After the contract is deployed, you will see a message in the console with the new contract address. Update the `CONTRACT_ADDRESS` in your `.env` file with this address.

5. Restart the Core service to pick up the new contract address:

   ```bash
   docker-compose restart core
   ```

## API Endpoints

All services have a Postman collection at the root of the directory which documents all endpoints.

## Running the Demo Script

For local setup:
```bash
python client_demo.py --producer-address <producer_wallet_address> --producer-key <producer_private_key> --consumer-address <consumer_wallet_address> --consumer-key <consumer_private_key>
```

For Docker setup:
```bash
docker exec -it ownit-core-1 python client_demo.py --producer-address <producer_wallet_address> --producer-key <producer_private_key> --consumer-address <consumer_wallet_address>  --consumer-key <consumer_private_key>
```

## Troubleshooting

### Cannot connect to the blockchain network

If you encounter an error indicating that the Core service cannot connect to the blockchain network, ensure that:

1. The `NETWORK_URL` in your `.env` file is set to `http://ganache:8545` if you are using docker, or `http://127.0.01:8545`  if you are running it local

2. The Ganache service is running and healthy. You can check its status with:
   ```bash
   docker-compose ps ganache
   ```
3. You can also grab a pair of accounts and private keys from the ganache logs
   ```bash
      docker logs ganache
   ```
3. If Ganache is not running, start it with:
   ```bash
   docker-compose up -d ganache
   ```
4. If the issue persists, try restarting all services:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Contract deployment fails

If the contract deployment fails:

1. Ensure Ganache is running and healthy.
2. Check the logs of the contract-deployer service:
   ```bash
   docker-compose logs contract-deployer
   ```
3. If necessary, you can manually run the contract deployment:
   ```bash
   docker-compose run --rm contract-deployer
   ```

Remember to update the `CONTRACT_ADDRESS` in your `.env` file and restart the Core service after a successful deployment.

## Security Considerations
- Ensure proper key management for wallet private keys
- Implement rate limiting and additional authentication for sensitive endpoints
- Regularly update dependencies and audit the codebase for vulnerabilities
- In a production environment, use a secure method to manage and inject the contract ABI and address
- Do not use the same accounts or private keys used in development for any production or mainnet deployments
- Ensure that the communication between services is secure, especially in a production environment
- When using Docker, be cautious about exposing ports and manage environment variables securely
