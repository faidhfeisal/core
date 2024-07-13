from encryption import encrypt, decrypt

def test_encryption():
    password = 'testpassword'
    data = 'This is a test.'

    encrypted = encrypt(data, password)
    assert encrypted is not None

    decrypted = decrypt(encrypted, password)
    assert decrypted.decode() == data

if __name__ == "__main__":
    test_encryption()
    print("All tests passed.")
