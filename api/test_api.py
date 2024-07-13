from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_create_did_endpoint():
    response = client.post("/create-did", json={})
    assert response.status_code == 200
    data = response.json()
    assert "did" in data
    assert "key" in data

if __name__ == "__main__":
    test_create_did_endpoint()
    print("API tests passed.")
