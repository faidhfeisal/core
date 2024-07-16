from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

app = FastAPI()

# Mock Store Service
class StoreRequest(BaseModel):
    file_path: str

class RetrieveRequest(BaseModel):
    ipfs_hash: str

stored_data = {}

def mock_get_public_key_from_did(did: str) -> bytes:
    # In a real implementation, this would fetch the public key from a DID resolver
    # For mock purposes, we'll use a fixed public key
    return bytes.fromhex("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")

@app.post("/store")
async def store_data(request: StoreRequest):
    ipfs_hash = f"Qm...{len(stored_data)}"
    stored_data[ipfs_hash] = request.file_path
    return {"ipfs_hash": ipfs_hash}

@app.post("/retrieve")
async def retrieve_data(request: RetrieveRequest):
    if request.ipfs_hash not in stored_data:
        raise HTTPException(status_code=404, detail="Data not found")
    return {"data": stored_data[request.ipfs_hash]}

# Mock Stream Service
class StreamRequest(BaseModel):
    streamId: str
    did: str
    proof: str

@app.post("/publish")
async def publish_stream(request: StreamRequest):
    return {"status": "published"}

@app.post("/subscribe")
async def subscribe_stream(request: StreamRequest):
    try:
        proof_obj = json.loads(request.proof)
        public_key = mock_get_public_key_from_did(request.did)
        
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
            return {"status": "subscribed", "streamId": request.streamId}
        except:
            raise HTTPException(status_code=403, detail="Invalid proof")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mock Transact Service
class DeployRequest(BaseModel):
    fromAddress: str

class InteractRequest(BaseModel):
    contractAddress: str
    methodName: str
    args: list
    fromAddress: str
    privateKey: str

@app.post("/deploy")
async def deploy_contract(request: DeployRequest):
    return {"contractAddress": "0x1234567890123456789012345678901234567890"}

@app.post("/interact")
async def interact_with_contract(request: InteractRequest):
    return {"txHash": "0x9876543210987654321098765432109876543210"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)