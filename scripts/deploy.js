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