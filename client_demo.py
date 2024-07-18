import asyncio
import aiohttp
import time
import json
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import os
from config import get_web3_url,NETWORK_URL,  PRODUCER_PRIVATE_KEY, CONSUMER_PRIVATE_KEY, PRODUCER_WALLET_ADDRESS, CONSUMER_WALLET_ADDRESS
import logging
web3 = Web3(Web3.HTTPProvider(NETWORK_URL))

logger = logging.getLogger(__name__)

async def connect_and_authenticate(session, wallet_address, private_key):
  # Connect wallet
    connect_response = await session.post("http://localhost:8000/connect-wallet", json={"address": wallet_address})
    connect_data = await connect_response.json()
    print("Wallet connected:", connect_data)
    nonce = connect_data["nonce"]

    # Authenticate wallet
    message = f"Authenticate to Data Marketplace with nonce: {nonce}"
    message_hash = encode_defunct(text=message)
    signed_message = web3.eth.account.sign_message(message_hash, private_key)

    auth_response = await session.post("http://localhost:8000/authenticate-wallet", json={
        "address": wallet_address,
        "signature": signed_message.signature.hex()
    })
    if auth_response.status == 200:
        auth_data = await auth_response.json()
        print("Wallet authenticated:", auth_data)
    else:
        error_data = await auth_response.json()
        print("Failed to authenticate wallet:", error_data)
        return 

    # Use the authenticated wallet address for subsequent requests
    headers = {"wallet-address": wallet_address}
    return headers


async def data_producer_journey(session, headers):
    print("\n--- Data Producer Journey ---")

    # Create a static asset
    print("\nCreating Static Asset:")
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
        print("Static asset added:", static_asset_data)
        static_asset_id = static_asset_data["asset_id"]
    else:
        print("Failed to add static asset:", await add_static_response.text())
        return None, None

    os.remove(test_file_path)

    # # Create a stream asset
    # print("\nCreating Stream Asset:")
    # stream_asset = {
    #     "name": "Test Stream Asset",
    #     "description": "A test stream asset created by a producer",
    #     "price": 50,
    #     "stream_id": "test_stream_id"
    # }
    
    # create_stream_response = await session.post("http://localhost:8000/producer/create-stream", 
    #                                             json=stream_asset, 
    #                                             headers=headers)
    # if create_stream_response.status == 200:
    #     stream_data = await create_stream_response.json()
    #     print("Stream created:", stream_data)
    #     stream_asset_id = stream_data["asset_id"]
    # else:
    #     print("Failed to create stream:", await create_stream_response.text())
    #     return static_asset_id, None

    # List assets
    print("\nListing Assets:")
    list_assets_response = await session.get("http://localhost:8000/producer/list-assets", headers=headers)
    if list_assets_response.status == 200:
        assets_data = await list_assets_response.json()
        print("Assets:", assets_data)
    else:
        print("Failed to list assets:", await list_assets_response.text())

    # Retrieve specific asset
    print(f"\nRetrieving Static Asset (ID: {static_asset_id}):")
    get_asset_response = await session.get(f"http://localhost:8000/producer/asset/{static_asset_id}", headers=headers)
    if get_asset_response.status == 200:
        asset_data = await get_asset_response.json()
        print("Retrieved asset:", asset_data)
    else:
        print("Failed to retrieve asset:", await get_asset_response.text())

     # Retrieve specific asset content
    print(f"\nRetrieving Static Asset Content (ID: {static_asset_id}):")
    get_asset_content_response = await session.get(f"http://localhost:8000/producer/asset-content/{static_asset_id}", headers=headers)
    if get_asset_content_response.status == 200:
        content = await get_asset_content_response.read()
        print(f"Retrieved asset content (first 100 bytes): {content[:100]}")

    return None, static_asset_id 


async def data_consumer_journey(session, headers):
    print("\n--- Data Consumer Journey ---")

    # List available assets
    print("\nListing available assets:")
    assets_response = await session.get("http://localhost:8000/consumer/list-assets", headers=headers)
    if assets_response.status == 200:
        assets = await assets_response.json()
        print("Available assets:", json.dumps(assets, indent=2))
    else:
        print("Failed to list assets:", await assets_response.text())
        return

    if not assets['assets']:
        print("No assets available for purchase.")
        return

    # Purchase an asset
    asset_to_purchase = assets['assets'][0]
    print(f"\nPurchasing asset (ID: {asset_to_purchase['id']}):")
    purchase_data = {"message": f"Purchase asset {asset_to_purchase['id']}"}
    purchase_response = await session.post(f"http://localhost:8000/consumer/purchase-asset/{asset_to_purchase['id']}", 
                                           json=purchase_data, headers=headers)
    if purchase_response.status == 200:
        purchase_result = await purchase_response.json()
        print("Purchase result:", json.dumps(purchase_result, indent=2))
    else:
        print("Failed to purchase asset:", await purchase_response.text())
        return

    # List purchased assets
    print("\nListing purchased assets:")
    my_assets_response = await session.get("http://localhost:8000/consumer/my-assets", headers=headers)
    if my_assets_response.status == 200:
        my_assets = await my_assets_response.json()
        print("My assets:", json.dumps(my_assets, indent=2))
    else:
        print("Failed to list purchased assets:", await my_assets_response.text())

    # Retrieve asset content
    print(f"\nRetrieving content for asset (ID: {asset_to_purchase['id']}):")
    content_response = await session.get(f"http://localhost:8000/consumer/asset-content/{asset_to_purchase['id']}", headers=headers)
    if content_response.status == 200:
        content = await content_response.json()

async def withdraw_revenue(session, headers):
    logger.info("--- Withdrawing Revenue ---")
    
    withdraw_response = await session.post("http://localhost:8000/producer/withdraw-revenue", headers=headers)
    
    print(f"Withdraw response status: {withdraw_response}")
    
    if withdraw_response.status == 200:
        withdraw_result = await withdraw_response.json()
        print(f"Withdraw result: {withdraw_result}")
        
        if withdraw_result.get("success"):
            print("Revenue withdrawn successfully. Transaction hash: %s", withdraw_result.get('tx_hash', 'N/A'))
            
            if 'amount' in withdraw_result:
                try:
                    amount_wei = int(withdraw_result['amount'])
                    amount_eth = Web3.from_wei(amount_wei, 'ether')
                    logger.info("Amount withdrawn: %s ETH", amount_eth)
                except ValueError:
                    logger.info(f"Invalid amount format: {withdraw_result['amount']}")
            else:
                print("Amount not provided in withdrawal result")
        else:
            print("Failed to withdraw revenue: %s", withdraw_result.get('message', 'No error message provided'))
    else:
        error_text = await withdraw_response.text()
        print(f"Failed to withdraw revenue. Status: {withdraw_response.status}, Response: {error_text}")

    print("--- End of Withdrawal Process ---")

async def main():
    async with aiohttp.ClientSession() as session:
        producer_wallet_info = await connect_and_authenticate(session, PRODUCER_WALLET_ADDRESS, PRODUCER_PRIVATE_KEY)
        consumer_wallet_info = await connect_and_authenticate(session, CONSUMER_WALLET_ADDRESS, CONSUMER_PRIVATE_KEY)
        
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
    asyncio.run(main())