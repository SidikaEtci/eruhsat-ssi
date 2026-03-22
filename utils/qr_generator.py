"""
QR Code Generator - Simple & Clean
"""
import qrcode
import json
from pathlib import Path
import config
from PIL import Image, ImageDraw, ImageFont


class QRCodeManager:
    """Generate simple QR codes with essential info"""
    
    @staticmethod
    def generate_qr_code(credential: dict, license_id: str) -> str:
        """
        Generate clean QR code with:
        - License number
        - Validity period
        - Digital signature
        - Verification URL
        """
        
        subject = credential["credentialSubject"]
        
        # Create clean, readable text
        qr_text = f"""━━━━━━━━━━━━━━━━━━━━━━━
KONYA E-RUHSAT
━━━━━━━━━━━━━━━━━━━━━━━

🆔 Ruhsat No:
{subject["licenseId"]}

📅 Geçerlilik:
{subject["validUntil"]}

🔐 Dijital İmza:
{credential["proof"]["proofValue"][:30]}...

━━━━━━━━━━━━━━━━━━━━━━━
✅ Online Doğrulama:
http://localhost:8000/verify-qr/{subject["licenseId"]}

📱 Herhangi bir QR okuyucu
ile taranabilir.
━━━━━━━━━━━━━━━━━━━━━━━"""
        
        # Generate QR
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=7,
            border=4,
        )
        
        qr.add_data(qr_text)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.convert('RGB')
        
        # Get size
        width, height = img.size
        
        # Add label at bottom
        new_img = Image.new('RGB', (width, height + 50), 'white')
        new_img.paste(img, (0, 0))
        
        # Add text
        draw = ImageDraw.Draw(new_img)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
        except:
            font = ImageFont.load_default()
        
        # License number
        text1 = f"Ruhsat: {license_id}"
        try:
            bbox = draw.textbbox((0, 0), text1, font=font)
            text_width = bbox[2] - bbox[0]
        except:
            text_width = len(text1) * 8
        
        draw.text(((width - text_width) // 2, height + 8), text1, fill='black', font=font)
        
        # URL hint
        try:
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            font_small = ImageFont.load_default()
        
        text2 = "Tarayın → Bilgileri Görün"
        try:
            bbox2 = draw.textbbox((0, 0), text2, font=font_small)
            text_width2 = bbox2[2] - bbox2[0]
        except:
            text_width2 = len(text2) * 6
        
        draw.text(((width - text_width2) // 2, height + 30), text2, fill='#667eea', font=font_small)
        
        # Save
        qr_path = config.QR_CODES_DIR / f"{license_id}.png"
        new_img.save(qr_path)
        
        print(f"\n✅ QR Code generated: {qr_path}")
        print(f"   📱 Scannable with any QR reader")
        print(f"   🔗 URL: http://localhost:8000/verify-qr/{license_id}")
        
        return str(qr_path)
    
    @staticmethod
    def parse_qr_code(qr_data_string: str) -> dict:
        """Parse QR code data"""
        try:
            return json.loads(qr_data_string)
        except:
            return None