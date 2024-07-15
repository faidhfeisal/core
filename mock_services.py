from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Mock Store Service
class StoreRequest(BaseModel):
    file_path: str

class RetrieveRequest(BaseModel):
    ipfs_hash: str

stored_data = {}

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
    data: dict
    did: str
    proof: str

@app.post("/publish")
async def publish_stream(request: StreamRequest):
    return {"status": "published"}

@app.post("/subscribe")
async def subscribe_stream(request: StreamRequest):
    return {"status": "subscribed", "streamId": request.streamId}

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