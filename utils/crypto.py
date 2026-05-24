"""Cryptographic utilities for symmetric/asymmetric encryption and digital signatures"""
import os
import json
import base64
import hashlib
import logging
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

# Setup logger for cryptographic operations
logger = logging.getLogger(__name__)

class AsymmetricCrypto:
    """
    RSA-based asymmetric hybrid encryption class.
    Strictly matches the naming convention required by your backend API endpoints.
    """
    @staticmethod
    def generate_keypair():
        """Generate RSA key pair (4096-bit)"""
        logger.info("Generating a new 4096-bit RSA key pair...")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        logger.info("RSA key pair generated successfully.")
        return private_key, public_key
    
    @staticmethod
    def encrypt_document(data: bytes, public_key) -> bytes:
        """Encrypt with public key (hybrid: RSA + AES)"""
        logger.info("Initiating hybrid asymmetric encryption for document payload...")
        
        # Generate random AES key
        logger.info("Generating secure random 256-bit AES key and Initialization Vector (IV)...")
        aes_key = os.urandom(32)  # 256-bit
        iv = os.urandom(16)
        
        # Encrypt data with AES
        logger.info("Applying symmetric AES-CBC encryption to the document data...")
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        
        # Padding
        padder = sym_padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Encrypt AES key with RSA public key
        logger.info("Encrypting symmetric AES key using RSA OAEP public key architecture...")
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Combine: encrypted_key_length + encrypted_key + iv + encrypted_data
        logger.info("Asymmetric hybrid encryption completed successfully. Packing output stream.")
        return len(encrypted_aes_key).to_bytes(4, 'big') + encrypted_aes_key + iv + encrypted_data

    @staticmethod
    def decrypt_document(encrypted_data: bytes, private_key) -> bytes:
        """Decrypt with private key"""
        logger.info("Initiating hybrid asymmetric decryption for document payload...")
        
        try:
            # Parse header metadata
            logger.info("Parsing encrypted envelope header...")
            key_length = int.from_bytes(encrypted_data[:4], 'big')
            logger.info(f"Extracted metadata -> Encrypted AES key length: {key_length} bytes.")
            
            # Slice payload segments
            encrypted_aes_key = encrypted_data[4:4+key_length]
            iv = encrypted_data[4+key_length:4+key_length+16]
            ciphertext = encrypted_data[4+key_length+16:]
            
            logger.info(f"Successfully unpacked envelope components:")
            logger.info(f" -> Encrypted AES key block: {len(encrypted_aes_key)} bytes")
            logger.info(f" -> Initialization Vector (IV): {iv.hex()}")
            logger.info(f" -> Encrypted document payload (ciphertext): {len(ciphertext)} bytes")
            
            # Decrypt AES key with RSA
            logger.info("Step 1: Attempting RSA private key decryption to recover symmetric AES key...")
            aes_key = private_key.decrypt(
                encrypted_aes_key,
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            logger.info("Step 1 Success: Symmetric AES key recovered successfully.")
            
            # Decrypt data with AES
            logger.info("Step 2: Re-initializing AES-CBC cipher suite and processing ciphertext decryption...")
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            logger.info(f"Step 2 Success: Ciphertext decrypted. Padded raw size: {len(padded_data)} bytes.")
            
            # Unpad
            logger.info("Step 3: Stripping symmetric PKCS7 block padding from the uncompressed stream...")
            unpadder = sym_padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            
            logger.info(f"Step 3 Success: Padding stripped clean. Final recovered document size: {len(data)} bytes.")
            logger.info("Asymmetric hybrid decryption completed seamlessly.")
            return data

        except ValueError as padding_err:
            logger.error("DECRYPTION ERROR: Symmetric unpadding failed. The data buffer might be corrupted or manipulated.")
            raise padding_err
        except Exception as crypto_err:
            logger.error(f"DECRYPTION CRITICAL FAILURE: Asymmetric resolution crashed. Exception info: {str(crypto_err)}")
            raise crypto_err


class CryptoManager:
    """
    Symmetric and signing utility manager.
    Keeps all decentralized identity (DID) and signature verifications running.
    """
    @staticmethod
    def generate_encryption_key(license_id: str) -> bytes:
        logger.info(f"Deriving safe encryption key for License ID: {license_id} via PBKDF2...")
        password = f"{license_id}_{config.ENCRYPTION_SECRET}".encode()
        salt = hashlib.sha256(license_id.encode()).digest()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=config.AES_KEY_SIZE,
            salt=salt,
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(password))
        logger.info("Symmetric encryption key derived successfully.")
        return derived_key

    @staticmethod
    def encrypt_file(file_path: str, key: bytes) -> bytes:
        logger.info(f"Encrypting local file via Fernet architecture at: {file_path}")
        cipher = Fernet(key)
        with open(file_path, 'rb') as f:
            file_data = f.read()
        encrypted_bytes = cipher.encrypt(file_data)
        logger.info("File contents encrypted successfully.")
        return encrypted_bytes

    @staticmethod
    def calculate_hash(file_path: str) -> str:
        logger.info(f"Computing SHA-256 integrity hash for asset at: {file_path}")
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        checksum = sha256.hexdigest()
        logger.info(f"SHA-256 hash calculation complete. Checksum: {checksum}")
        return checksum

    @staticmethod
    def generate_keypair(seed: str = None):
        if seed:
            logger.info("Generating Ed25519 key pair derived from deterministic seed...")
            seed_bytes = seed.encode().ljust(32, b'0')[:32]
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes)
        else:
            logger.info("Generating fresh random Ed25519 key pair...")
            private_key = ed25519.Ed25519PrivateKey.generate()
        
        logger.info("Ed25519 decentralized identity keys generated.")
        return private_key, private_key.public_key()

    @staticmethod
    def sign_data(data: dict, private_key) -> str:
        logger.info("Serializing dictionary payload and signing with Ed25519 private key...")
        data_bytes = json.dumps(data, sort_keys=True).encode()
        encoded_signature = base64.b64encode(private_key.sign(data_bytes)).decode()
        logger.info("Digital signature computed and base64 encoded successfully.")
        return encoded_signature

    @staticmethod
    def verify_signature(data: dict, signature: str, public_key) -> bool:
        logger.info("Verifying Ed25519 identity signature against data dictionary payload...")
        try:
            data_bytes = json.dumps(data, sort_keys=True).encode()
            public_key.verify(base64.b64decode(signature), data_bytes)
            logger.info("Cryptographic Signature is VALID.")
            return True
        except Exception as e:
            logger.warning(f"Cryptographic Signature is INVALID or TAMPERED. Verification failed: {str(e)}")
            return False
    
