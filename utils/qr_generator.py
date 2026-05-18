"""QR code generation for license credentials."""
import qrcode
from pathlib import Path
import config
from PIL import Image, ImageDraw, ImageFont


class QRCodeManager:
    """Generate scannable QR codes with essential license info."""

    @staticmethod
    def generate_qr_code(credential: dict, license_id: str) -> str:
        subject = credential["credentialSubject"]

        qr_payload = f"""-------------------------
KONYA E-LICENSE
-------------------------

License No:
{subject["licenseId"]}

Business:
{subject.get("businessName", "Not specified")}

Region: {subject["region"]}

Valid until:
{subject["validUntil"]}

Digital signature:
{credential["proof"]["proofValue"][:30]}...

-------------------------
Online verification:
http://localhost:8000/verify-qr/{subject["licenseId"]}

Scan with any QR reader.
-------------------------"""

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=7,
            border=4,
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        width, height = img.size

        new_img = Image.new("RGB", (width, height + 50), "white")
        new_img.paste(img, (0, 0))
        draw = ImageDraw.Draw(new_img)

        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13
            )
            font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10
            )
        except OSError:
            font = ImageFont.load_default()
            font_small = font

        text1 = f"License: {license_id}"
        text2 = "Scan to view details"

        for text, y_offset, use_font in (
            (text1, height + 8, font),
            (text2, height + 30, font_small),
        ):
            try:
                bbox = draw.textbbox((0, 0), text, font=use_font)
                text_width = bbox[2] - bbox[0]
            except AttributeError:
                text_width = len(text) * 8
            color = "#667eea" if y_offset > height + 20 else "black"
            draw.text(
                ((width - text_width) // 2, y_offset),
                text,
                fill=color,
                font=use_font,
            )

        qr_path = config.QR_CODES_DIR / f"{license_id}.png"
        new_img.save(qr_path)

        print(f"\n   QR code generated: {qr_path}")
        print(f"     URL: http://localhost:8000/verify-qr/{license_id}")

        return str(qr_path)
