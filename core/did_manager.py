import asyncio
import logging
import json
from typing import Dict, Any
import didkit
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def create_did() -> tuple[str, str]:
    try:
        key = didkit.generate_ed25519_key()
        did = didkit.key_to_did("key", key)
        logger.info(f"Created new DID: {did}")
        return did, key
    except Exception as e:
        logger.error(f"Failed to create DID: {str(e)}")
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