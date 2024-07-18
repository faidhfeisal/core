from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import json
import logging

logger = logging.getLogger(__name__)

class KeyManager:
    def __init__(self, master_password):
        salt = b'salt_'  # In production, use a secure random salt and store it
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self.fernet = Fernet(key)
        self.keys = {}

    def add_key(self, did, private_key):
        logger.debug(f"Adding key for DID: {did}")
        logger.debug(f"Key to be added (first 10 chars): {private_key[:10]}...")
        encrypted_key = self.fernet.encrypt(private_key.encode()).decode()
        self.keys[did] = encrypted_key

    def get_key(self, did):
        logger.debug(f"Retrieving key for DID: {did}")
        encrypted_key = self.keys.get(did)
        if encrypted_key:
            decrypted_key = self.fernet.decrypt(encrypted_key.encode()).decode()
            logger.debug(f"Retrieved key (first 10 chars): {decrypted_key[:10]}...")
            return decrypted_key
        logger.warning(f"No key found for DID: {did}")
        return None

    def save_to_file(self, filename):
        logger.info(f"Saving keys to file: {filename}")
        with open(filename, 'w') as f:
            json.dump(self.keys, f)

    def load_from_file(self, filename):
        logger.info(f"Loading keys from file: {filename}")
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                self.keys = json.load(f)
            logger.debug(f"Loaded {len(self.keys)} keys")
        else:
            logger.warning(f"Key file not found: {filename}")

# Initialize the KeyManager (in a real-world scenario, you'd use a secure way to input the master password)
key_manager = KeyManager("master_password")

def get_private_key(did):
    return key_manager.get_key(did)

def add_private_key(did, private_key):
    key_manager.add_key(did, private_key)

# Save keys to file (call this when adding or updating keys)
def save_keys():
    key_manager.save_to_file('keys.json')

# Load keys from file (call this when initializing the application)
def load_keys():
    key_manager.load_from_file('keys.json')

load_keys()