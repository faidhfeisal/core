import asyncio
import aiohttp
import time
import json
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import os
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def connect_and_authenticate(session, wallet_address, private_key):
    # Connect wallet
    connect_response = await session.post("http://localhost:8000/connect-wallet", json={"address": wallet_address})
    connect_data = await connect_response.json()
    logger.info("Wallet connected: %s", connect_data)
    nonce = connect_data["nonce"]

    # Authenticate wallet
    message = f"Authenticate to Data Marketplace with nonce: {nonce}"
    message_hash = encode_defunct(text=message)
    signed_message = Web3().eth.account.sign_message(message_hash, private_key)

    auth_response = await session.post("http://localhost:8000/authenticate-wallet", json={
        "address": wallet_address,
        "signature": signed_message.signature.hex()
    })
    if auth_response.status == 200:
        auth_data = await auth_response.json()
        logger.info("Wallet authenticated: %s", auth_data)
    else:
        error_data = await auth_response.json()
        logger.error("Failed to authenticate wallet: %s", error_data)
        return 

    # Use the authenticated wallet address for subsequent requests
    headers = {"wallet-address": wallet_address}
    return headers

async def data_producer_journey(session, headers):
    logger.info("--- Data Producer Journey ---")

    # Create a static asset
    logger.info("Creating Static Asset:")
    test_file_path = "test_static_asset.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test static asset for the data marketplace.")
    set_price = Web3.to_wei(0.00000000000000001, 'ether')
    form_data = aiohttp.FormData()
    form_data.add_field('file', open(test_file_path, 'rb'), filename='test_static_asset.txt')
    form_data.add_field('name', 'Test Static Asset')
    form_data.add_field('description', 'A test static asset created by a producer')
    form_data.add_field('price', str(set_price))

    add_static_response = await session.post("http://localhost:8000/producer/add-static-asset", data=form_data, headers=headers)
    if add_static_response.status == 200:
        static_asset_data = await add_static_response.json()
        logger.info("Static asset added: %s", static_asset_data)
        static_asset_id = static_asset_data["asset_id"]
    else:
        logger.error("Failed to add static asset: %s", await add_static_response.text())
        return None, None

    os.remove(test_file_path)

    # Create a stream asset
    logger.info("Creating Stream Asset:")
    stream_asset = {
        "name": "Test Stream Asset",
        "description": "A test stream asset created by a producer",
        "price": 50,
        "stream_id": "test_stream_id"
    }
    
    create_stream_response = await session.post("http://localhost:8000/producer/create-stream", 
                                                json=stream_asset, 
                                                headers=headers)
    if create_stream_response.status == 200:
        stream_data = await create_stream_response.json()
        logger.info("Stream created: %s", stream_data)
        stream_asset_id = stream_data["asset_id"]
    else:
        logger.error("Failed to create stream: %s", await create_stream_response.text())
        return None, static_asset_id

    # List assets
    logger.info("Listing Assets:")
    list_assets_response = await session.get("http://localhost:8000/producer/list-assets", headers=headers)
    if list_assets_response.status == 200:
        assets_data = await list_assets_response.json()
        logger.info("Assets: %s", assets_data)
    else:
        logger.error("Failed to list assets: %s", await list_assets_response.text())

    return stream_asset_id, static_asset_id 

async def data_consumer_journey(session, headers):
    logger.info("--- Data Consumer Journey ---")

    # List available assets
    logger.info("Listing available assets:")
    assets_response = await session.get("http://localhost:8000/consumer/list-assets", headers=headers)
    if assets_response.status == 200:
        assets = await assets_response.json()
        logger.info("Available assets: %s", json.dumps(assets, indent=2))
    else:
        logger.error("Failed to list assets: %s", await assets_response.text())
        return

    if not assets['assets']:
        logger.info("No assets available for purchase.")
        return

    # Purchase an asset
    asset_to_purchase = assets['assets'][0]
    logger.info("Purchasing asset (ID: %s):", asset_to_purchase['id'])
    purchase_data = {"message": f"Purchase asset {asset_to_purchase['id']}"}
    purchase_response = await session.post(f"http://localhost:8000/consumer/purchase-asset/{asset_to_purchase['id']}", 
                                           json=purchase_data, headers=headers)
    if purchase_response.status == 200:
        purchase_result = await purchase_response.json()
        logger.info("Purchase result: %s", json.dumps(purchase_result, indent=2))
    else:
        logger.error("Failed to purchase asset: %s", await purchase_response.text())
        return

    # List purchased assets
    logger.info("Listing purchased assets:")
    my_assets_response = await session.get("http://localhost:8000/consumer/my-assets", headers=headers)
    if my_assets_response.status == 200:
        my_assets = await my_assets_response.json()
        logger.info("My assets: %s", json.dumps(my_assets, indent=2))
    else:
        logger.error("Failed to list purchased assets: %s", await my_assets_response.text())

async def withdraw_revenue(session, headers):
    logger.info("--- Withdrawing Revenue ---")
    
    withdraw_response = await session.post("http://localhost:8000/producer/withdraw-revenue", headers=headers)
    
    if withdraw_response.status == 200:
        withdraw_result = await withdraw_response.json()
        logger.info("Withdraw result: %s", withdraw_result)
        
        if withdraw_result.get("success"):
            logger.info("Revenue withdrawn successfully. Transaction hash: %s", withdraw_result.get('tx_hash', 'N/A'))
            
            if 'amount' in withdraw_result:
                try:
                    amount_wei = int(withdraw_result['amount'])
                    amount_eth = Web3.from_wei(amount_wei, 'ether')
                    logger.info("Amount withdrawn: %s ETH", amount_eth)
                except ValueError:
                    logger.info("Invalid amount format: %s", withdraw_result['amount'])
            else:
                logger.info("Amount not provided in withdrawal result")
        else:
            logger.info("Failed to withdraw revenue: %s", withdraw_result.get('message', 'No error message provided'))
    else:
        error_text = await withdraw_response.text()
        logger.error("Failed to withdraw revenue. Status: %s, Response: %s", withdraw_response.status, error_text)

    logger.info("--- End of Withdrawal Process ---")

async def main(producer_address, producer_key, consumer_address, consumer_key):
    async with aiohttp.ClientSession() as session:
        producer_wallet_info = await connect_and_authenticate(session, producer_address, producer_key)
        consumer_wallet_info = await connect_and_authenticate(session, consumer_address, consumer_key)
        
        if producer_wallet_info and consumer_wallet_info:
            # Producer journey
            await data_producer_journey(session, producer_wallet_info)
            
            # Consumer journey
            await data_consumer_journey(session, consumer_wallet_info)

            # Wait a bit to ensure transactions are processed
            await asyncio.sleep(15)

            # Producer withdraws revenue
            await withdraw_revenue(session, producer_wallet_info)
        else:
            logger.error("Failed to authenticate wallets. Aborting demo.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the OwnIt AI Data Asset Layer 2 demo")
    parser.add_argument("--producer-address", required=True, help="Producer wallet address")
    parser.add_argument("--producer-key", required=True, help="Producer private key")
    parser.add_argument("--consumer-address", required=True, help="Consumer wallet address")
    parser.add_argument("--consumer-key", required=True, help="Consumer private key")
    args = parser.parse_args()

    asyncio.run(main(args.producer_address, args.producer_key, args.consumer_address, args.consumer_key))