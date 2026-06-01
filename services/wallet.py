"""
Aries-style Digital Wallet service for e-Ruhsat SSI platform.

Architecture
────────────
- Holder identity  = Aries holder id (prefer DID format)
- Holder DID       = provided DID or derived local DID
- VC issuance      = municipality signs with Ed25519 (existing flow)
- VP presentation  = one-time backend-minted presentation token
- Verification     = challenge + token + holder id checks on backend
"""
import json
import uuid
from datetime import datetime, timedelta

import config
from utils.wallet_storage import (
    accept_pending_offer,
    add_pending_offer,
    consume_challenge,
    get_credential,
    get_credentials,
    get_pending_offers,
    get_wallet,
    save_wallet,
    store_challenge,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(holder_id: str) -> str:
    """Normalize holder identifier for lookup/storage."""
    return holder_id.strip().lower()


def _holder_did(holder_id: str) -> str:
    normalized = _normalize(holder_id)
    if normalized.startswith("did:"):
        return normalized
    encoded = normalized.replace(":", "-")
    return f"did:key:{encoded}"


# ── Wallet Service ────────────────────────────────────────────────────────────

class WalletService:
    """Manages Aries-style citizen wallets for the e-Ruhsat platform."""

    # ── Register / Lookup ─────────────────────────────────────────────────────

    def register_wallet(self, holder_id: str, display_name: str = "") -> dict:
        """
        Register a holder wallet on the backend.
        Holder id should typically be a DID from an Aries wallet.
        """
        hid = _normalize(holder_id)
        existing = get_wallet(hid)
        if existing:
            return {
                "holder_id": hid,
                "did": existing["did"],
                "display_name": existing.get("display_name", ""),
                "created_at": existing["created_at"],
                "already_existed": True,
            }

        wallet_data = {
            "holder_id": hid,
            "did": _holder_did(hid),
            "display_name": display_name or f"Aries Holder {hid[:10]}…",
            "credentials": [],
            "pending_offers": [],
            "created_at": datetime.now().isoformat() + "Z",
        }
        save_wallet(hid, wallet_data)
        print(f"   [Wallet] Registered: {hid} → {_holder_did(hid)}")

        return {
            "holder_id": hid,
            "did": _holder_did(hid),
            "display_name": wallet_data["display_name"],
            "created_at": wallet_data["created_at"],
            "already_existed": False,
        }

    def get_wallet_summary(self, holder_id: str) -> dict | None:
        wallet = get_wallet(_normalize(holder_id))
        if not wallet:
            return None
        return {
            "holder_id": wallet["holder_id"],
            "did": wallet["did"],
            "display_name": wallet.get("display_name", ""),
            "created_at": wallet["created_at"],
            "credential_count": len(wallet.get("credentials", [])),
            "pending_offer_count": len(wallet.get("pending_offers", [])),
        }

    # ── Credential Offer (Issuer → Wallet) ────────────────────────────────────

    def offer_credential(self, holder_id: str, credential: dict) -> dict:
        """
        Municipality sends a VC offer to the citizen's wallet.
        The citizen must explicitly accept before the VC is stored.
        """
        hid = _normalize(holder_id)
        offer_id = str(uuid.uuid4())
        license_id = credential.get("credentialSubject", {}).get("licenseId", "unknown")

        offer = {
            "offer_id": offer_id,
            "license_id": license_id,
            "credential": credential,
            "issuer_name": credential.get("issuer", {}).get("name", "Unknown Authority"),
            "offered_at": datetime.now().isoformat() + "Z",
        }

        if not add_pending_offer(hid, offer):
            # Wallet not registered yet — auto-register
            self.register_wallet(hid)
            add_pending_offer(hid, offer)

        print(f"   [Wallet] Offer sent to {hid}: license={license_id}")
        return {"offer_id": offer_id, "license_id": license_id}

    def list_offers(self, holder_id: str) -> list:
        offers = get_pending_offers(_normalize(holder_id))
        return [
            {
                "offer_id": o["offer_id"],
                "license_id": o["license_id"],
                "issuer_name": o.get("issuer_name", "Unknown"),
                "offered_at": o["offered_at"],
            }
            for o in offers
        ]

    def accept_offer(self, holder_id: str, offer_id: str) -> dict:
        """Citizen accepts an offer → VC moved from pending to accepted credentials."""
        result = accept_pending_offer(_normalize(holder_id), offer_id)
        if not result:
            raise ValueError(f"Offer {offer_id} not found or already accepted.")
        print(f"   [Wallet] Offer {offer_id} accepted by {_normalize(holder_id)[:10]}…")
        return {"accepted": True, "license_id": result["license_id"]}

    # ── Challenge Generation (step 1 of VP flow) ──────────────────────────────

    def create_challenge(self, holder_id: str, license_id: str) -> dict:
        """
        Generate a one-time Aries-style presentation challenge.
        Returns a short-lived presentation token for QR transfer.
        """
        hid = _normalize(holder_id)
        credential = get_credential(hid, license_id)
        if not credential:
            raise ValueError(f"Credential {license_id} not found in wallet {hid}")

        challenge_id = str(uuid.uuid4())
        presentation_token = str(uuid.uuid4())
        expires_at = (datetime.now() + timedelta(minutes=5)).isoformat() + "Z"

        store_challenge(challenge_id, {
            "holder_id": hid,
            "license_id": license_id,
            "presentation_token": presentation_token,
            "expires_at": expires_at,
        })

        print(f"   [Wallet] Challenge created for {license_id}, id={challenge_id[:8]}…")
        return {
            "challenge_id": challenge_id,
            "presentation_token": presentation_token,
            "expires_at": expires_at,
        }

    # ── Verify Presentation (step 2 — after MetaMask signs) ───────────────────

    def verify_presentation(
        self,
        challenge_id: str,
        holder_id: str,
        presentation_token: str,
    ) -> dict:
        """
        Verify an Aries-style Verifiable Presentation.

        Checks:
          1. Challenge exists and has not been used before (anti-replay)
          2. Challenge has not expired
          3. Holder id matches original challenge binding
          4. Presentation token matches one-time challenge token
          4. Embedded VC issuer signature is valid (Ed25519)
          5. VC has not expired
        """
        # 1. Consume challenge (one-time use)
        challenge = consume_challenge(challenge_id)
        if not challenge:
            return {
                "valid": False,
                "reason": "challenge_invalid",
                "message": "This QR code has already been used or does not exist.",
            }

        # 2. Expiry check
        expires_at = datetime.fromisoformat(
            challenge["expires_at"].replace("Z", "+00:00")
        )
        if datetime.now(expires_at.tzinfo) > expires_at:
            return {
                "valid": False,
                "reason": "challenge_expired",
                "message": "This QR code has expired. Please generate a new one.",
            }

        # 3. Holder id must match the one challenge was created for
        hid = _normalize(holder_id)
        if hid != challenge.get("holder_id"):
            return {
                "valid": False,
                "reason": "holder_mismatch",
                "message": "Presentation holder does not match challenge holder.",
            }

        # 4. One-time presentation token check
        if presentation_token != challenge.get("presentation_token"):
            return {
                "valid": False,
                "reason": "token_invalid",
                "message": "Presentation token is invalid.",
            }

        # 5 & 6. Verify the embedded VC (issuer signature + expiry)
        credential = get_credential(hid, challenge["license_id"])
        if not credential:
            return {
                "valid": False,
                "reason": "credential_not_found",
                "message": "Credential not found in wallet.",
            }

        vc_result = self._verify_vc(credential)
        if not vc_result["valid"]:
            return vc_result

        subject = credential.get("credentialSubject", {})
        return {
            "valid": True,
            "message": "License verified successfully via Aries wallet.",
            "holder_id": hid,
            "holder_did": _holder_did(hid),
            "license": {
                "license_id": subject.get("licenseId"),
                "license_type": subject.get("licenseType"),
                "business_name": subject.get("businessName"),
                "city": subject.get("city"),
                "region": subject.get("region"),
                "valid_from": subject.get("validFrom"),
                "valid_until": subject.get("validUntil"),
                "authority": credential.get("issuer", {}).get("name"),
            },
        }

    def _verify_vc(self, vc: dict) -> dict:
        """Re-verify the municipality's Ed25519 signature on an embedded VC."""
        from cities import get_city
        from utils.crypto import CryptoManager

        try:
            proof = vc.get("proof")
            if not proof:
                return {"valid": False, "reason": "no_vc_proof",
                        "message": "VC has no proof block."}

            city_slug = vc.get("credentialSubject", {}).get("citySlug", config.CITY_SLUG)
            city = get_city(city_slug)
            _, public_key = CryptoManager.generate_keypair(seed=city["issuer_seed"])

            vc_copy = {k: v for k, v in vc.items() if k != "proof"}
            canonical = json.dumps(vc_copy, sort_keys=True, ensure_ascii=False)

            if not CryptoManager.verify_signature(canonical, proof["proofValue"], public_key):
                return {"valid": False, "reason": "invalid_issuer_signature",
                        "message": "Municipality signature on the VC is invalid."}

            exp = vc.get("expirationDate")
            if exp:
                exp_dt = datetime.fromisoformat(exp.replace("Z", ""))
                if datetime.now() > exp_dt:
                    return {"valid": False, "reason": "vc_expired",
                            "message": "The credential has expired."}

            return {"valid": True}

        except Exception as exc:
            return {"valid": False, "reason": "vc_verify_error", "message": str(exc)}

    # ── Credential list ───────────────────────────────────────────────────────

    def list_credentials(self, holder_id: str) -> list:
        creds = get_credentials(_normalize(holder_id))
        result = []
        for cred in creds:
            s = cred.get("credentialSubject", {})
            result.append({
                "license_id": s.get("licenseId"),
                "license_type": s.get("licenseType"),
                "business_name": s.get("businessName"),
                "city": s.get("city"),
                "region": s.get("region"),
                "valid_from": s.get("validFrom"),
                "valid_until": s.get("validUntil"),
                "authority": cred.get("issuer", {}).get("name"),
                "stored_at": cred.get("stored_at"),
            })
        return result