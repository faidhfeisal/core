from did_manager import create_did, verify_did, get_verification_method

def test_create_did():
    did, key = create_did()
    assert did.startswith("did:key:")

def test_verify_did():
    did, key = create_did()
    verification_method = get_verification_method(key)
    assert verify_did(did, verification_method)

if __name__ == "__main__":
    test_create_did()
    test_verify_did()
    print("All tests passed.")
