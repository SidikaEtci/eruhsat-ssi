"""QR Code generation with simplified structure"""
import qrcode
import json
from pathlib import Path
from datetime import datetime
import config

class QRCodeManager:
    """Simple QR code manager"""
    
    @staticmethod
    def generate_qr_code(license_data: dict, signature: str, private_key) -> str:
        """Generate simple QR code"""
        
        # SIMPLE payload - just essential data
        qr_payload = {
            "license_id": license_data.get("license_id"),
            "license_type": license_data.get("license_type"),
            "owner_name": license_data.get("owner_name"),
            "citizen_id": license_data.get("citizen_id"),
            "region": license_data.get("region"),
            "issue_date": license_data.get("issue_date"),
            "expiry_date": license_data.get("expiry_date"),
            "authority": license_data.get("authority"),
            "ipfs_hash": license_data.get("ipfs_hash", ""),
            "document_hash": license_data.get("document_hash", ""),
            "created_at": license_data.get("created_at", datetime.now().isoformat())
        }
        
        # Convert to JSON string
        qr_data_string = json.dumps(qr_payload, ensure_ascii=False)
        
        print(f"\n📱 Generating QR Code...")
        print(f"QR Data Preview: {qr_data_string[:100]}...")
        
        # Create QR code
        qr = qrcode.QRCode(
            version=10,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        
        qr.add_data(qr_data_string)
        qr.make(fit=True)
        
        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save
        save_path = config.QR_CODES_DIR / f"{license_data['license_id']}.png"
        img.save(save_path)
        
        print(f"✅ QR code saved: {save_path}")
        print(f"📊 Data size: {len(qr_data_string)} characters")
        
        return str(save_path)
    
    @staticmethod
    def parse_qr_code(qr_data_string: str) -> dict:
        """Parse QR code JSON"""
        try:
            data = json.loads(qr_data_string)
            print(f"✅ QR Parsed: {data.get('license_id')}")
            return data
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            return None