"""Issuer Service - Issues digital licenses to citizens"""
import json
from datetime import datetime
from pathlib import Path
import config
from utils.crypto import CryptoManager
from utils.ipfs_manager import IPFSManager
from utils.qr_generator import QRCodeManager
from utils.blockchain_logger import BlockchainLogger
from utils.verifiable_credentials import VerifiableCredentialManager
from contracts.license_contract import LicenseContract


class LicenseIssuer:
    """Issue digital licenses with QR codes and IPFS storage"""

    def __init__(self):
        # Initialize keys and IPFS
        self.private_key, self.public_key = CryptoManager.generate_keypair(
            seed=config.ISSUER_SEED
        )
        self.ipfs = IPFSManager()
        self.blockchain = BlockchainLogger()
        self.vc_manager = VerifiableCredentialManager()
        self.contract = LicenseContract()
        print("   License Issuer Initialized")
        print("   Smart Contract initialized")

    def issue_license(self, license_data: dict, pdf_path: str = None) -> dict:
        """Process and issue a new decentralized license"""
        print(f"\n--- ISSUING LICENSE: {license_data['license_id']} ---")

        # Smart Contract Validation FIRST
        contract_result = self.contract.issue_license(
            license_data,
            config.ISSUER_DID
        )
        
        if not contract_result["success"]:
            # Business rules failed!
            print(f"   Smart Contract Rejected: {contract_result['message']}")
            raise Exception(f"Smart Contract: {contract_result['message']}")
        
        print(f"   Smart Contract Approved")

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

        # 2. Create Verifiable Credential (W3C Standard)
        credential = self.vc_manager.create_credential(license_data)
        print("   Verifiable Credential created (privacy-preserving)")

        # 3. Generate QR Code (with VC, NO sensitive data)
        qr_url = QRCodeManager.generate_qr_code(credential, license_data['license_id'])

        # 4. Add to blockchain
        self.blockchain.add_block({
            "action": "ISSUE_LICENSE",
            "credential": credential,
            "ipfs_hash": license_data.get('ipfs_hash', ''),
        })

        # 5. Save to Local Database (include VC)
        license_data['verifiable_credential'] = credential
        self._save_to_db(license_data, qr_url)

        return {
            "success": True,
            "ipfs_hash": license_data.get('ipfs_hash'),
            "qr_url": f"/data/qr_codes/{license_data['license_id']}.png",
            "credential": credential
        }

    def _save_to_db(self, data, qr_url):
        """Save license to database"""
        db_path = config.DATA_DIR / "credentials.json"
        db = []
        
        if db_path.exists():
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    db = json.load(f)
            except:
                db = []
        
        data['created_at'] = datetime.now().isoformat()
        data['qr_url'] = qr_url
        db.append(data)
        
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        
        print(f"   Saved to database: {data['license_id']}")

    def get_license_info(self, license_id: str):
        """Get license information by ID"""
        db_path = config.DATA_DIR / "credentials.json"
        
        if not db_path.exists():
            print(f"   Database not found: {db_path}")
            return None
        
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            
            print(f"  Searching for: '{license_id}'")
            
            for item in db:
                if not item:
                    continue
                
                item_id = item.get('license_id', '')
                
                if str(item_id).strip() == str(license_id).strip():
                    print(f"   Found: {license_id}")
                    return item
            
            print(f"   Not found: {license_id}")
            return None
            
        except Exception as e:
            print(f"   Database error: {e}")
            return None