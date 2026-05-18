"""Cryptographic utilities for symmetric/asymmetric encryption and digital signatures"""
import os
import json
import base64
import hashlib
import config

# Cryptography imports for existing functionality (Fernet & Ed25519)
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

# Cryptography imports for Asymmetric RSA Hybrid Encryption
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.backends import default_backend

class AsymmetricCrypto:
    """
    RSA-based asymmetric hybrid encryption class.
    Strictly matches the naming convention required by your backend API endpoints.
    """
    @staticmethod
    def generate_keypair():
        """Generate RSA key pair (4096-bit)"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    @staticmethod
    def encrypt_document(data: bytes, public_key) -> bytes:
        """Encrypt with public key (hybrid: RSA + AES)"""
        # Generate random AES key
        aes_key = os.urandom(32)  # 256-bit
        iv = os.urandom(16)
        
        # Encrypt data with AES
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        
        # Padding
        padder = sym_padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Encrypt AES key with RSA public key
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Combine: encrypted_key_length + encrypted_key + iv + encrypted_data
        return len(encrypted_aes_key).to_bytes(4, 'big') + encrypted_aes_key + iv + encrypted_data

    @staticmethod
    def decrypt_document(encrypted_data: bytes, private_key) -> bytes:
        """Decrypt with private key"""
        # Extract encrypted AES key
        key_length = int.from_bytes(encrypted_data[:4], 'big')
        encrypted_aes_key = encrypted_data[4:4+key_length]
        iv = encrypted_data[4+key_length:4+key_length+16]
        ciphertext = encrypted_data[4+key_length+16:]
        
        # Decrypt AES key with RSA
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt data with AES
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Unpad
        unpadder = sym_padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data


class CryptoManager:
    """
    Symmetric and signing utility manager.
    Keeps all decentralized identity (DID) and signature verifications running.
    """
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