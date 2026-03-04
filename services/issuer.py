"""Issuer Service - Issues digital licenses to citizens"""
import json
from datetime import datetime
from pathlib import Path
import config
from utils.crypto import CryptoManager
from utils.ipfs_manager import IPFSManager
from utils.qr_generator import QRCodeManager

class LicenseIssuer:
    """Issue digital licenses with QR codes and IPFS storage"""
    
    def __init__(self):
        # Initialize keys and IPFS
        self.private_key, self.public_key = CryptoManager.generate_keypair(
            seed=config.ISSUER_SEED
        )
        self.ipfs = IPFSManager()
        print("✅ License Issuer Initialized")

    def issue_license(self, license_data: dict, pdf_path: str = None) -> dict:
        """Process and issue a new decentralized license"""
        print(f"\n--- ISSUING LICENSE: {license_data['license_id']} ---")
        
        # Add authority info
        license_data['authority'] = config.ISSUER_NAME
        
        # 1. Upload PDF to IPFS (Encrypted)
        ipfs_data = None
        if pdf_path:
            ipfs_data = self.ipfs.upload_encrypted_document(
                pdf_path, 
                license_data['license_id']
            )
            license_data['ipfs_hash'] = ipfs_data['ipfs_hash']
            license_data['document_hash'] = ipfs_data['document_hash']

        # 2. Digital Signing
        # We sign the core data to ensure integrity
        signing_payload = {
            "license_id": license_data['license_id'],
            "license_type": license_data['license_type'],
            "authority": license_data['authority'],
            "status": "Active"
        }
        signature = CryptoManager.sign_data(signing_payload, self.private_key)

        # 3. Generate QR Code
        qr_url = QRCodeManager.generate_qr_code(
            license_data,
            signature,
            self.private_key
        )

        # 4. Save to Local Database (Simulation of Ledger)
        self._save_to_db(license_data, qr_url)
        
        return {
            "success": True,
            "ipfs_hash": license_data.get('ipfs_hash'),
            "qr_url": f"/data/qr_codes/{license_data['license_id']}.png"
        }

    def _save_to_db(self, data, qr_url):
        db_path = config.DATA_DIR / "credentials.json"
        db = []
        if db_path.exists():
            with open(db_path, 'r') as f: db = json.load(f)
        data['created_at'] = datetime.now().isoformat()
        db.append(data)
        with open(db_path, 'w') as f: json.dump(db, f, indent=2)

# services/issuer.py içinde bul ve değiştir:
def get_license_info(self, license_id: str):
    db_path = config.DATA_DIR / "credentials.json"
    if not db_path.exists(): return None
    with open(db_path, 'r') as f:
        db = json.load(f)
        for item in db:
            # .get() kullanarak anahtar yoksa çökmesini engelliyoruz
            if item.get('license_id') == license_id: 
                return item
    return None