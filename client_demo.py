import asyncio
import aiohttp
import time
import json
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import os
from config import get_web3_url,GANACHE_URL,  WALLET_ADDRESS, WALLET_PRIVATE_KEY
import logging
web3 = Web3(Web3.HTTPProvider(GANACHE_URL))

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

async def generate_zkproof(wallet_address: str, message: str) -> str:
    private_key = WALLET_PRIVATE_KEY
    
    # Create the message to sign
    message_to_sign = f"{wallet_address}:{message}:{int(time.time())}"
    message_hash = encode_defunct(text=message_to_sign)
    
    # Sign the message
    signed_message = web3.eth.account.sign_message(message_hash, private_key=private_key)
    
    # Create the proof object
    proof = {
        "r": hex(signed_message.r),
        "s": hex(signed_message.s),
        "message": message_to_sign
    }
    
    return json.dumps(proof)

async def data_producer_journey(session, headers):
    print("\n--- Data Producer Journey ---")

    # Create a static asset
    print("\nCreating Static Asset:")
    test_file_path = "test_static_asset.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test static asset for the data marketplace.")

    form_data = aiohttp.FormData()
    form_data.add_field('file', open(test_file_path, 'rb'), filename='test_static_asset.txt')
    form_data.add_field('name', 'Test Static Asset')
    form_data.add_field('description', 'A test static asset created by a producer')
    form_data.add_field('price', '100')

    add_static_response = await session.post("http://localhost:8000/producer/add-static-asset", data=form_data, headers=headers)
    if add_static_response.status == 200:
        static_asset_data = await add_static_response.json()
        print("Static asset added:", static_asset_data)
        static_asset_id = static_asset_data["asset_id"]
    else:
        print("Failed to add static asset:", await add_static_response.text())
        return None, None

    os.remove(test_file_path)

    # Create a stream asset
    print("\nCreating Stream Asset:")
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
        print("Stream created:", stream_data)
        stream_asset_id = stream_data["asset_id"]
    else:
        print("Failed to create stream:", await create_stream_response.text())
        return static_asset_id, None

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

    # Delete static asset
    print(f"\nDeleting Static Asset (ID: {static_asset_id}):")
    delete_asset_response = await session.delete(f"http://localhost:8000/producer/asset/{static_asset_id}", headers=headers)
    if delete_asset_response.status == 200:
        delete_data = await delete_asset_response.json()
        print("Asset deleted:", delete_data)
    else:
        print("Failed to delete asset:", await delete_asset_response.text())

    return stream_asset_id, None  # We're not returning static_asset_id as it's been deleted


async def data_consumer_journey(session, headers, static_asset_id, stream_asset_id):
    print("\n--- Data Consumer Journey ---")

    if static_asset_id is None and stream_asset_id is None:
        print("No valid asset IDs provided. Skipping consumer journey.")
        return

    # Static Asset Operations
    if static_asset_id is not None:
        print("\nStatic Asset Operations:")
        # Purchase static asset
        purchase_data = {"message": f"Purchase static asset {static_asset_id}"}
        purchase_response = await session.post(f"http://localhost:8000/consumer/purchase-asset/{static_asset_id}", 
                                               json=purchase_data, headers=headers)
        if purchase_response.status == 200:
            purchase_result = await purchase_response.json()
            print("Static asset purchased:", purchase_result)
        else:
            print("Failed to purchase static asset:", await purchase_response.text())

        # Access static asset
        access_response = await session.get(f"http://localhost:8000/consumer/access-static-asset/{static_asset_id}", headers=headers)
        if access_response.status == 200:
            access_result = await access_response.json()
            print("Accessed static asset:", access_result)
        else:
            print("Failed to access static asset:", await access_response.text())

    # Stream Operations
    if stream_asset_id is not None:
        print("\nStream Operations:")
        # Subscribe to stream
        subscribe_data = {"stream_id": "test_stream_id"}
        subscribe_response = await session.post("http://localhost:8000/consumer/subscribe-stream", 
                                                json=subscribe_data, headers=headers)
        if subscribe_response.status == 200:
            subscribe_result = await subscribe_response.json()
            print("Subscribed to stream:", subscribe_result)
        else:
            print("Failed to subscribe to stream:", await subscribe_response.text())

        # Access stream
        access_stream_response = await session.get(f"http://localhost:8000/consumer/access-stream/{stream_asset_id}", headers=headers)
        if access_stream_response.status == 200:
            stream_data = await access_stream_response.json()
            print("Accessed stream:", stream_data)
        else:
            print("Failed to access stream:", await access_stream_response.text())

async def main():
    async with aiohttp.ClientSession() as session:
        wallet_address = WALLET_ADDRESS
        private_key = WALLET_PRIVATE_KEY

        headers = await connect_and_authenticate(session, wallet_address, private_key)
        if headers:
            static_asset_id, stream_asset_id = await data_producer_journey(session, headers)
            await data_consumer_journey(session, headers, static_asset_id, stream_asset_id)

if __name__ == "__main__":
    asyncio.run(main())