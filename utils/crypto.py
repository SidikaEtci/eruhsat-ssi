"""Cryptographic utilities for encryption and digital signatures"""
import hashlib
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import config

class CryptoManager:
    @staticmethod
    def generate_encryption_key(license_id: str) -> bytes:
        password = f"{license_id}_{config.ENCRYPTION_SECRET}".encode()
        salt = hashlib.sha256(license_id.encode()).digest()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=config.AES_KEY_SIZE,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password))

    @staticmethod
    def encrypt_file(file_path: str, key: bytes) -> bytes:
        cipher = Fernet(key)
        with open(file_path, 'rb') as f:
            return cipher.encrypt(f.read())

    @staticmethod
    def calculate_hash(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.hexdigest()

    @staticmethod
    def generate_keypair(seed: str = None):
        if seed:
            seed_bytes = seed.encode().ljust(32, b'0')[:32]
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes)
        else:
            private_key = ed25519.Ed25519PrivateKey.generate()
        return private_key, private_key.public_key()

    @staticmethod
    def sign_data(data: dict, private_key) -> str:
        data_bytes = json.dumps(data, sort_keys=True).encode()
        return base64.b64encode(private_key.sign(data_bytes)).decode()

    @staticmethod
    def verify_signature(data: dict, signature: str, public_key) -> bool:
        try:
            data_bytes = json.dumps(data, sort_keys=True).encode()
            public_key.verify(base64.b64decode(signature), data_bytes)
            return True
        except:
            return False