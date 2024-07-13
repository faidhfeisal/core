import subprocess
import json

def create_did():
    # Generate a new Ed25519 key
    key = subprocess.check_output(["didkit", "generate-ed25519-key"]).strip()
    key_json = key.decode('utf-8')
    
    # Convert the key to a DID
    did = subprocess.check_output(["didkit", "key-to-did", "--jwk", key_json]).strip()
    return did.decode('utf-8'), key_json

def get_verification_method(key_json):
    # Convert the key to a verification method
    verification_method = subprocess.check_output(["didkit", "key-to-verification-method", "--jwk", key_json, "key"]).strip()
    return verification_method.decode('utf-8')

def verify_did(did, verification_method):
    # The DID should start with the part of the verification method before the fragment
    return did == verification_method.split('#')[0]

if __name__ == "__main__":
    did, key = create_did()
    verification_method = get_verification_method(key)
    print("DID:", did)
    print("Key:", key)
    print("Verification Method:", verification_method)
    print("Verification:", verify_did(did, verification_method))
