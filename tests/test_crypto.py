from pwmgr.crypto import encrypt_json, decrypt_json

def test_encrypt_decrypt_roundtrip():
    obj = {"hello": "world", "n": 123}
    blob = encrypt_json(obj, "master123!")
    out = decrypt_json(blob, "master123!")
    assert out == obj

def test_wrong_password_fails():
    obj = {"a": 1}
    blob = encrypt_json(obj, "good")
    try:
        decrypt_json(blob, "bad")
        assert False, "Should have failed"
    except ValueError:
        assert True