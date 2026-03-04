"""QR Code generation for offline license verification"""
import qrcode
import json
from datetime import datetime
import config

class QRCodeManager:
    @staticmethod
    def generate_qr_code(license_data: dict, signature: str, private_key) -> str:
        # Prepare English payload
        qr_payload = {
            "v": "1.0",
            "type": "license_verification",
            "data": {
                "id": license_data.get("license_id"),
                "type": license_data.get("license_type"),
                "owner": license_data.get("owner_name"),
                "expiry": license_data.get("expiry_date"),
                "auth": config.ISSUER_NAME
            },
            "sig": signature
        }

        qr = qrcode.QRCode(version=5, box_size=10, border=4)
        qr.add_data(json.dumps(qr_payload))
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        save_path = config.QR_CODES_DIR / f"{license_data['license_id']}.png"
        img.save(save_path)
        
        return str(save_path)