"""
QR Code Generation for Verifiable Credentials
Uses W3C VC standard - NO sensitive data in QR
"""
import qrcode
import json
from pathlib import Path
import config
from datetime import datetime


class QRCodeManager:
    """Generate QR codes for Verifiable Credentials"""
    
    @staticmethod
    def generate_qr_code(credential: dict, license_id: str) -> str:
        """
        Generate QR code containing Verifiable Credential
        
        QR contains:
        ✅ Credential ID (for lookup)
        ✅ License type
        ✅ Region
        ✅ Validity status
        ✅ Issuer DID
        ✅ Cryptographic proof
        
        QR does NOT contain:
        ❌ TC kimlik
        ❌ İsim
        ❌ Adres
        ❌ Telefon
        """
        
        # Prepare QR data (minimal, privacy-preserving)
        qr_data = {
            "@context": "https://www.w3.org/2018/credentials/v1",
            "type": "VerifiableCredentialQR",
            "credentialId": credential["credentialSubject"]["licenseId"],
            "licenseType": credential["credentialSubject"]["licenseType"],
            "region": credential["credentialSubject"]["region"],
            "issuer": credential["issuer"]["id"],
            "validUntil": credential["credentialSubject"]["validUntil"],
            "proof": credential["proof"]["proofValue"],
            "verificationUrl": f"https://konya.gov.tr/verify/{license_id}",
            "timestamp": datetime.now().isoformat()
        }
        
        # Convert to JSON
        qr_json = json.dumps(qr_data, ensure_ascii=False)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=config.QR_VERSION,
            error_correction=getattr(qrcode.constants, f'ERROR_CORRECT_{config.QR_ERROR_CORRECTION}'),
            box_size=config.QR_BOX_SIZE,
            border=config.QR_BORDER,
        )
        
        qr.add_data(qr_json)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save
        qr_path = config.QR_CODES_DIR / f"{license_id}.png"
        img.save(qr_path)
        
        print(f"✅ QR Code generated: {qr_path}")
        print(f"   Privacy-preserving: NO sensitive data")
        
        return str(qr_path)
    
    @staticmethod
    def parse_qr_code(qr_data_string: str) -> dict:
        """Parse QR code data"""
        try:
            return json.loads(qr_data_string)
        except:
            return None