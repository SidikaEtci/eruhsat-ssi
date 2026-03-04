"""
Configuration file for Konya E-Ruhsat System
"""
import os
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
KEYS_DIR = DATA_DIR / "keys"
DOCUMENTS_DIR = DATA_DIR / "documents"
QR_CODES_DIR = DATA_DIR / "qr_codes"

# Create directories if they don't exist
for directory in [DATA_DIR, KEYS_DIR, DOCUMENTS_DIR, QR_CODES_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# Blockchain configuration
GENESIS_TXN_PATH = "/tmp/genesis.txn"
POOL_NAME = "konya_pool"

# IPFS configuration
IPFS_HOST = "127.0.0.1"
IPFS_PORT = 5001

# Issuer configuration (Konya Municipality)
ISSUER_DID = "did:indy:konya:KBB"
ISSUER_NAME = "Konya Buyuksehir Belediyesi"
ISSUER_SEED = "konya_belediyesi_seed_000000000001"  # 32 characters

# Schema configuration
SCHEMA_NAME = "ERuhsat"
SCHEMA_VERSION = "1.0"
SCHEMA_ATTRIBUTES = [
    "ruhsat_no",
    "ruhsat_turu",
    "belediye",
    "verilme_tarihi",
    "gecerlilik_tarihi",
    "bolge",
    "ipfs_hash",
    "document_hash"
]

# Security
ENCRYPTION_SECRET = "konya_encryption_secret_2024"  # Change in production!
AES_KEY_SIZE = 32  # 256 bits

# QR Code configuration
QR_VERSION = 10
QR_ERROR_CORRECTION = "H"  # High error correction
QR_BOX_SIZE = 10
QR_BORDER = 4
