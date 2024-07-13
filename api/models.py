from pydantic import BaseModel

class DIDRequest(BaseModel):
    pass

class DIDResponse(BaseModel):
    did: str
    key: str
