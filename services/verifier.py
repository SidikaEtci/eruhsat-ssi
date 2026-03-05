"""
License Verifier - Simple version
"""
import json
from pathlib import Path
import config

class LicenseVerifier:
    """Verify licenses"""
    
    def __init__(self):
        print("✅ License Verifier Initialized")
    
    def verify_license(self, license_id: str) -> dict:
        """Simple verification from database"""
        db_path = config.DATA_DIR / "credentials.json"
        
        if not db_path.exists():
            return {
                'valid': False,
                'message': 'Database not found'
            }
        
        with open(db_path, 'r', encoding='utf-8') as f:
            credentials = json.load(f)
        
        for cred in credentials:
            if cred.get('license_id') == license_id:
                return {
                    'valid': True,
                    'message': 'Valid license',
                    'data': cred
                }
        
        return {
            'valid': False,
            'message': 'License not found'
        }