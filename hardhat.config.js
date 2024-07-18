// hardhat.config.js
require("@nomiclabs/hardhat-waffle");

module.exports = {
  solidity: "0.8.0",
  networks: {
    localhost: {
      url: "http://ganache:8545",
      timeout: 60000 // Increase timeout to 1 minute
    }
  }
};