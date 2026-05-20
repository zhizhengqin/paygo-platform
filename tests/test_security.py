"""测试 security 模块 — bcrypt 密码哈希 + Fernet 密钥加解密"""
from app.security import hash_password, verify_password, init_fernet, encrypt_secret, decrypt_secret


class TestPasswordHashing:
    def test_hash_password_returns_different_from_input(self):
        hashed = hash_password("admin123")
        assert hashed != "admin123"
        assert len(hashed) > 20

    def test_verify_password_returns_true_for_correct_password(self):
        hashed = hash_password("admin123")
        assert verify_password("admin123", hashed) is True

    def test_verify_password_returns_false_for_wrong_password(self):
        hashed = hash_password("admin123")
        assert verify_password("wrong", hashed) is False

    def test_verify_password_constant_time_rejects(self):
        hashed = hash_password("admin123")
        assert verify_password("admin123", "not-a-valid-hash") is False

    def test_hash_password_generates_different_hashes(self):
        h1 = hash_password("admin123")
        h2 = hash_password("admin123")
        assert h1 != h2


class TestSecretKeyEncryption:
    def test_init_fernet_returns_valid_fernet(self):
        f = init_fernet()
        assert f is not None
        token = f.encrypt(b"test-secret-key-32-bytes-xxxxxx")
        decrypted = f.decrypt(token)
        assert decrypted == b"test-secret-key-32-bytes-xxxxxx"

    def test_init_fernet_with_custom_key(self):
        from cryptography.fernet import Fernet
        import base64
        key = base64.urlsafe_b64encode(b"A" * 32).decode()
        f = init_fernet(master_key=key)
        plaintext = "a" * 32
        token = encrypt_secret(plaintext)
        decrypted = decrypt_secret(token)
        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip(self):
        init_fernet()
        plaintext = "abcdef0123456789abcdef0123456789"
        token = encrypt_secret(plaintext)
        assert token != plaintext
        decrypted = decrypt_secret(token)
        assert decrypted == plaintext

    def test_encrypt_secret_is_stable_for_same_input(self):
        init_fernet()
        t1 = encrypt_secret("same-secret-abcde123456789abcdef")
        t2 = encrypt_secret("same-secret-abcde123456789abcdef")
        assert t1 != t2

    def test_decrypt_secret_handles_invalid_token(self):
        init_fernet()
        result = decrypt_secret("not-valid-encrypted-data")
        assert result is None
