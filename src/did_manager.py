import asyncio
import logging
import json
from typing import Dict, Any
import didkit
from fastapi import HTTPException
import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature

from key_management import add_private_key, get_private_key, save_keys

logger = logging.getLogger(__name__)

class ZKProof:
    def __init__(self):
        self.curve = ec.SECP256K1()

    def generate_proof(self, private_key: str, message: str) -> str:
        logger.debug(f"Generating proof with private key (first 10 chars): {private_key[:10]}...")
        logger.debug(f"Private key length: {len(private_key)}")

        try:
            # Parse the JSON-encoded key
            key_data = json.loads(private_key)
            if key_data['kty'] != 'OKP' or key_data['crv'] != 'Ed25519':
                raise ValueError("Unsupported key type")
            
            # Extract the actual key material
            d = base64.urlsafe_b64decode(key_data['d'] + '==')
            logger.debug(f"Extracted key length: {len(d)} bytes")

            # Convert Ed25519 private key to SECP256K1
            private_key_bytes = self.ed25519_to_secp256k1(d)

        except json.JSONDecodeError:
            logger.warning("Private key is not JSON. Attempting to use as-is.")
            private_key_bytes = base64.b64decode(private_key)

        logger.debug(f"Final private key length: {len(private_key_bytes)} bytes")

        private_key_int = int.from_bytes(private_key_bytes, 'big')
        private_key_obj = ec.derive_private_key(private_key_int, self.curve)
        
        signature = private_key_obj.sign(
            message.encode(),
            ec.ECDSA(hashes.SHA256())
        )
        r, s = decode_dss_signature(signature)
        
        return json.dumps({
            "r": hex(r),
            "s": hex(s),
            "message": message
        })

    def ed25519_to_secp256k1(self, ed25519_key: bytes) -> bytes:
        # This is a simplification. In practice, you'd need a more robust conversion
        hasher = hashes.Hash(hashes.SHA256())
        hasher.update(ed25519_key)
        return hasher.finalize()

    @staticmethod
    def verify(proof: str, public_key: bytes) -> bool:
        proof_obj = json.loads(proof)
        r = int(proof_obj["r"], 16)
        s = int(proof_obj["s"], 16)
        message = proof_obj["message"].encode()
        
        public_key_obj = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), public_key)
        
        try:
            public_key_obj.verify(
                encode_dss_signature(r, s),
                message,
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except:
            return False

async def create_did() -> tuple[str, str]:
    try:
        key = didkit.generate_ed25519_key()
        did = didkit.key_to_did("key", key)
        add_private_key(did, key)
        save_keys()  # Save keys after adding a new one
        logger.info(f"Created new DID: {did}")
        logger.debug(f"Generated key (first 10 chars): {key[:10]}...")
        return did, key
    except Exception as e:
        logger.error(f"Failed to create DID: {str(e)}")
        raise

async def generate_zkproof(did: str, message: str) -> str:
    private_key = get_private_key(did)
    if not private_key:
        raise ValueError(f"No private key found for DID: {did}")
    logger.debug(f"Retrieved private key for DID {did} (first 10 chars): {private_key[:10]}...")
    zkp = ZKProof()
    try:
        proof = zkp.generate_proof(private_key, message)
        logger.debug(f"Generated proof: {proof[:50]}...")  # Log first 50 chars of the proof
        return proof
    except Exception as e:
        logger.error(f"Error generating proof: {str(e)}")
        raise

async def resolve_did(did: str) -> Dict:
    try:
        did_document = didkit.resolve_did(did, "{}")
        return json.loads(did_document)
    except didkit.DIDKitException as e:
        logger.error(f"Error resolving DID: {str(e)}")
        if "notFound" in str(e):
            raise HTTPException(status_code=404, detail="DID not found")
        else:
            raise HTTPException(status_code=500, detail="Error resolving DID")
    except Exception as e:
        logger.error(f"Unexpected error resolving DID: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error resolving DID")

async def verify_did(did: str, verification_method: str) -> bool:
    try:
        did_document = await resolve_did(did)
        return any(vm['id'] == verification_method for vm in did_document.get('verificationMethod', []))
    except Exception as e:
        logger.error(f"Error verifying DID: {str(e)}")
        return False

async def issue_credential(did: str, key: str, credential: Dict[str, Any]) -> str:
    try:
        verification_method = didkit.key_to_verification_method("key", key)
        
        options = {
            "proofPurpose": "assertionMethod",
            "verificationMethod": verification_method
        }
        
        signed_credential = didkit.issue_credential(
            json.dumps(credential),
            json.dumps(options),
            key
        )
        
        return signed_credential
    except Exception as e:
        logger.error(f"Error issuing credential: {str(e)}")
        raise

async def verify_credential(credential: str) -> bool:
    try:
        result = didkit.verify_credential(credential, "{}")
        return json.loads(result).get("verified", False)
    except didkit.DIDKitException as e:
        raise ValueError(f"Error verifying credential: {str(e)}")