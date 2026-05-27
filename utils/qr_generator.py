"""QR code generation — original credential QR + new wallet challenge QR."""
import qrcode
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ── Shared helper ─────────────────────────────────────────────────────────────

def _load_fonts():
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except OSError:
        font = ImageFont.load_default()
        font_small = font
    return font, font_small


def _make_qr_image(data: str) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=7,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _add_caption(img: Image.Image, lines: list[tuple[str, str]]) -> Image.Image:
    """Append text lines below a QR image. lines = [(text, color), ...]"""
    line_h = 22
    extra = line_h * len(lines) + 8
    width, height = img.size
    new_img = Image.new("RGB", (width, height + extra), "white")
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    font, font_small = _load_fonts()

    for i, (text, color) in enumerate(lines):
        use_font = font if i == 0 else font_small
        try:
            bbox = draw.textbbox((0, 0), text, font=use_font)
            tw = bbox[2] - bbox[0]
        except AttributeError:
            tw = len(text) * 8
        y = height + 4 + i * line_h
        draw.text(((width - tw) // 2, y), text, fill=color, font=use_font)
    return new_img


# ── QR Code Manager ───────────────────────────────────────────────────────────

class QRCodeManager:
    """Generate scannable QR codes for e-Ruhsat licenses."""

    # ── Original credential QR (kept for backward compat) ────────────────────

    @staticmethod
    def generate_qr_code(
        credential: dict,
        license_id: str,
        city: dict,
        qr_codes_dir: Path,
    ) -> str:
        """
        Legacy QR: embeds verification URL + partial credential info.
        Still used when no wallet is involved.
        """
        subject = credential["credentialSubject"]
        base_url = __import__("config").PUBLIC_BASE_URL.rstrip("/")

        qr_payload = (
            f"{city['name'].upper()} E-LICENSE\n\n"
            f"License No: {subject['licenseId']}\n"
            f"City: {subject.get('city', city['name'])}\n"
            f"District: {subject['region']}\n"
            f"Business: {subject.get('businessName', 'Not specified')}\n"
            f"Valid until: {subject['validUntil']}\n"
            f"Digital signature: {credential['proof']['proofValue'][:30]}...\n"
            f"Online verification: {base_url}/verify-qr/{subject['licenseId']}"
        )

        img = _make_qr_image(qr_payload)
        img = _add_caption(img, [
            (f"{city['name']}: {license_id}", "black"),
            ("Scan to view details", "#667eea"),
        ])

        qr_codes_dir.mkdir(parents=True, exist_ok=True)
        qr_path = qr_codes_dir / f"{license_id}.png"
        img.save(qr_path)
        print(f"   QR code generated: {qr_path}")
        return str(qr_path)

    # ── NEW: Wallet challenge QR ──────────────────────────────────────────────

    @staticmethod
    def generate_wallet_qr(
        challenge_id: str,
        verify_url: str,
        license_id: str,
    ) -> str:
        """
        Wallet QR: encodes ONLY the one-time challenge URL.
        The actual credential never travels through the QR —
        the verifier fetches the VP from the backend after scanning.

        This prevents:
          • QR screenshot sharing
          • Replay attacks (challenge is consumed on first use)
          • Credential data exposure
        """
        # QR just carries the URL — no credential data embedded
        img = _make_qr_image(verify_url)
        img = _add_caption(img, [
            (f"E-Ruhsat: {license_id}", "black"),
            ("Wallet QR · Valid 5 min · Single use", "#e53e3e"),
        ])

        out_dir = Path(__import__("config").DATA_ROOT) / "wallet_qr"
        out_dir.mkdir(parents=True, exist_ok=True)
        qr_path = out_dir / f"{license_id}_{challenge_id[:8]}.png"
        img.save(qr_path)
        print(f"   Wallet QR generated: {qr_path}")
        return str(qr_path)
