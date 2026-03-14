"""
QR Code with Verifiable Credential
Offline verification - no internet required
"""
import qrcode
import json
from pathlib import Path
import config
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont


class QRCodeManager:
    """Generate QR codes with Verifiable Credentials for offline verification"""
    
    @staticmethod
    def generate_qr_code(credential: dict, license_id: str) -> str:
        """
        Generate QR code containing Verifiable Credential
        
        QR contains FULL VC with cryptographic proof
        Can be verified OFFLINE (no internet needed)
        """
        
        # Create compact VC for QR (remove unnecessary fields)
        qr_credential = {
            "@context": credential["@context"][0],
            "type": credential["type"],
            "issuer": {
                "id": credential["issuer"]["id"],
                "name": credential["issuer"]["name"]
            },
            "issuanceDate": credential["issuanceDate"],
            "credentialSubject": {
                "id": credential["credentialSubject"]["id"],
                "licenseId": credential["credentialSubject"]["licenseId"],
                "licenseType": credential["credentialSubject"]["licenseType"],
                "region": credential["credentialSubject"]["region"],
                "validFrom": credential["credentialSubject"]["validFrom"],
                "validUntil": credential["credentialSubject"]["validUntil"]
            },
            "proof": {
                "type": credential["proof"]["type"],
                "created": credential["proof"]["created"],
                "proofValue": credential["proof"]["proofValue"]
            }
        }
        
        # Convert to compact JSON (no whitespace)
        qr_data = json.dumps(qr_credential, separators=(',', ':'), ensure_ascii=False)
        
        print(f"\n📏 QR Data Size: {len(qr_data)} bytes")
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=None,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.convert('RGB')
        
        # Add label
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        # Add text
        width, height = img.size
        new_img = Image.new('RGB', (width, height + 50), 'white')
        new_img.paste(img, (0, 0))
        
        draw = ImageDraw.Draw(new_img)
        
        # License ID
        text1 = f"Ruhsat No: {license_id}"
        bbox = draw.textbbox((0, 0), text1, font=font)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, height + 5), text1, fill='black', font=font)
        
        # Offline verification label
        text2 = "✓ Çevrimdışı Doğrulanabilir"
        bbox2 = draw.textbbox((0, 0), text2, font=font)
        text_width2 = bbox2[2] - bbox2[0]
        draw.text(((width - text_width2) // 2, height + 25), text2, fill='green', font=font)
        
        # Save
        qr_path = config.QR_CODES_DIR / f"{license_id}.png"
        new_img.save(qr_path)
        
        print(f"✅ QR Code generated: {qr_path}")
        print(f"   Contains: Verifiable Credential (offline verification)")
        print(f"   Privacy: NO personal data (TC, name)")
        
        return str(qr_path)
    
    @staticmethod
    def parse_qr_code(qr_data_string: str) -> dict:
        """Parse QR code data"""
        try:
            return json.loads(qr_data_string)
        except:
            return None