import asyncio
import aiohttp
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import os
from config import get_web3_url, WALLET_ADDRESS, WALLET_PRIVATE_KEY

async def main():
    # Connect to the network
    w3 = Web3(Web3.HTTPProvider(get_web3_url()))

    # For demo purposes, we'll create a new account
    # In a real scenario, you'd use a real wallet
    # account = w3.eth.account.create()
    wallet_address = WALLET_ADDRESS
    private_key = WALLET_PRIVATE_KEY

    print(f"Using wallet address: {wallet_address}")
    async with aiohttp.ClientSession() as session:
        # Connect wallet
        connect_response = await session.post("http://localhost:8000/connect-wallet", json={"address": wallet_address})
        connect_data = await connect_response.json()
        print("Wallet connected:", connect_data)
        nonce = connect_data["nonce"]

        # Authenticate wallet
        message = f"Authenticate to Data Marketplace with nonce: {nonce}"
        message_hash = encode_defunct(text=message)
        signed_message = w3.eth.account.sign_message(message_hash, private_key)

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

        # Create a test file
        test_file_path = "test_file.txt"
        with open(test_file_path, "w") as f:
            f.write("This is a test file for the data marketplace.")

        # Add a static asset
        static_asset = {
            "name": "Test Static Asset",
            "description": "A test static asset",
            "price": 100,
            "is_stream": False,
            "data": test_file_path
        }
        add_static_response = await session.post("http://localhost:8000/add-asset", json=static_asset, headers=headers)
        static_asset_data = await add_static_response.json()
        print("Static asset added:", static_asset_data)
        static_asset_id = static_asset_data["asset_id"]

        # Add a stream asset
        stream_asset = {
            "name": "Test Stream Asset",
            "description": "A test stream asset",
            "price": 200,
            "is_stream": True,
            "data": "test_stream_id"
        }
        add_stream_response = await session.post("http://localhost:8000/add-asset", json=stream_asset, headers=headers)
        stream_asset_data = await add_stream_response.json()
        print("Stream asset added:", stream_asset_data)
        stream_asset_id = stream_asset_data["asset_id"]

        # Purchase static asset
        try:
            purchase_response = await session.post(f"http://localhost:8000/purchase-asset/{static_asset_id}", headers=headers)
            if purchase_response.status == 200:
                purchase_data = await purchase_response.json()
                print("Static asset purchased:", purchase_data)
            else:
                error_text = await purchase_response.text()
                print(f"Failed to purchase static asset. Status: {purchase_response.status}, Detail: {error_text}")
        except Exception as e:
            print(f"Error purchasing static asset: {str(e)}")

        # Subscribe to stream
        try:
            subscribe_response = await session.post("http://localhost:8000/subscribe-stream", json={"stream_id": "test_stream_id"}, headers=headers)
            if subscribe_response.status == 200:
                subscribe_data = await subscribe_response.json()
                print("Subscribed to stream:", subscribe_data)
            else:
                error_text = await subscribe_response.text()
                print(f"Failed to subscribe to stream. Status: {subscribe_response.status}, Detail: {error_text}")
        except Exception as e:
            print(f"Error subscribing to stream: {str(e)}")

        # Access static asset
        try:
            access_static_response = await session.get(f"http://localhost:8000/access-asset/{static_asset_id}", headers=headers)
            if access_static_response.status == 200:
                print("Accessed static asset:", await access_static_response.json())
            elif access_static_response.status == 403:
                print("Access denied: You do not own this asset")
            else:
                print(f"Failed to access static asset. Status: {access_static_response.status}")
        except Exception as e:
            print(f"Error accessing static asset: {str(e)}")

        # Access stream asset
        try:
            access_stream_response = await session.get(f"http://localhost:8000/access-asset/{stream_asset_id}", headers=headers)
            if access_stream_response.status == 200:
                print("Accessed stream asset:", await access_stream_response.json())
            elif access_stream_response.status == 403:
                print("Access denied: You do not own this asset")
            else:
                print(f"Failed to access stream asset. Status: {access_stream_response.status}")
        except Exception as e:
            print(f"Error accessing stream asset: {str(e)}")

        # Clean up
        os.remove(test_file_path)

if __name__ == "__main__":
    asyncio.run(main())