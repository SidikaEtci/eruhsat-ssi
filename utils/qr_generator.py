"""QR code generation for license credentials."""
import qrcode
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class QRCodeManager:
    """Generate scannable QR codes with essential license info."""

    @staticmethod
    def generate_qr_code(
        credential: dict,
        license_id: str,
        city: dict,
        qr_codes_dir: Path,
    ) -> str:
        subject = credential["credentialSubject"]
        base_url = __import__("config").PUBLIC_BASE_URL.rstrip("/")

        qr_payload = f"""
{city['name'].upper()} E-LICENSE

License No: {subject["licenseId"]}

City: {subject.get("city", city["name"])}

District: {subject["region"]}

Business: {subject.get("businessName", "Not specified")}

Valid until: {subject["validUntil"]}

Digital signature: {credential["proof"]["proofValue"][:30]}...

Online verification: {base_url}/verify-qr/{subject["licenseId"]}
"""

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

        for text, y_offset, use_font in (
            (f"{city['name']}: {license_id}", height + 8, font),
            ("Scan to view details", height + 30, font_small),
        ):
            try:
                bbox = draw.textbbox((0, 0), text, font=use_font)
                text_width = bbox[2] - bbox[0]
            except AttributeError:
                text_width = len(text) * 8
            color = "#667eea" if y_offset > height + 20 else "black"
            draw.text(((width - text_width) // 2, y_offset), text, fill=color, font=use_font)

        qr_codes_dir.mkdir(parents=True, exist_ok=True)
        qr_path = qr_codes_dir / f"{license_id}.png"
        new_img.save(qr_path)

        print(f"\n   QR code generated: {qr_path}")
        return str(qr_path)
