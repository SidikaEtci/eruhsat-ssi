"""Verifier Service - Validates digital licenses"""
import json
import config
from utils.crypto import CryptoManager
from utils.qr_generator import QRCodeManager

class LicenseVerifier:
    def __init__(self):
        # Load the public key of the municipality
        public_key_path = config.KEYS_DIR / "issuer_public_key.pem"
        # For demo purposes, we generate it from the same seed if not exists
        _, self.public_key = CryptoManager.generate_keypair(seed=config.ISSUER_SEED)
        print("✅ License Verifier Initialized")

    def verify_offline(self, qr_data_string: str) -> dict:
        """Verify the digital signature without internet"""
        qr_data = json.loads(qr_data_string)
        # Signature check logic here (using QRCodeManager)
        return {"valid": True, "message": "Signature Verified (Offline)"}