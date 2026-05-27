"""
MetaMask Digital Wallet service for e-Ruhsat SSI platform.

Architecture
────────────
- Holder identity  = Ethereum address from MetaMask (no server-side key gen)
- Holder DID       = did:ethr:0xAddress
- VC issuance      = municipality signs with Ed25519 (existing flow)
- VP signing       = MetaMask personal_sign (secp256k1, happens in browser)
- Verification     = eth_account.recover_message() on the backend

Flow
────
1. Citizen connects MetaMask in browser → address sent to POST /api/wallet/register
2. Municipality issues VC → POST /api/wallet/{address}/offer
3. Citizen accepts offer → POST /api/wallet/{address}/accept/{offer_id}
4. To present: GET /api/wallet/challenge/{license_id}  → gets challenge string
5. Browser: MetaMask signs the challenge string
6. POST /api/wallet/present  { address, license_id, challenge_id, signature }
7. Backend: recovers signer from signature → must match address → checks VC
"""
import json
import uuid
from datetime import datetime, timedelta

from eth_account import Account
from eth_account.messages import encode_defunct

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

def _normalize(address: str) -> str:
    """Lowercase + checksummed Ethereum address."""
    return address.lower()


def _eth_did(address: str) -> str:
    return f"did:ethr:{address.lower()}"


def _recover_signer(message: str, signature: str) -> str:
    """Recover Ethereum address from a personal_sign signature."""
    msg = encode_defunct(text=message)
    return Account.recover_message(msg, signature=signature).lower()


# ── Wallet Service ────────────────────────────────────────────────────────────

class WalletService:
    """Manages MetaMask-connected citizen wallets for the e-Ruhsat platform."""

    # ── Register / Lookup ─────────────────────────────────────────────────────

    def register_wallet(self, eth_address: str, display_name: str = "") -> dict:
        """
        Register a MetaMask wallet on the backend.
        The private key stays inside MetaMask — the backend only stores the
        public Ethereum address and the credentials associated with it.
        """
        addr = _normalize(eth_address)
        existing = get_wallet(addr)
        if existing:
            return {
                "address": addr,
                "did": existing["did"],
                "display_name": existing.get("display_name", ""),
                "created_at": existing["created_at"],
                "already_existed": True,
            }

        wallet_data = {
            "address": addr,
            "did": _eth_did(addr),
            "display_name": display_name or f"Wallet {addr[:6]}…{addr[-4:]}",
            "credentials": [],
            "pending_offers": [],
            "created_at": datetime.now().isoformat() + "Z",
        }
        save_wallet(addr, wallet_data)
        print(f"   [Wallet] Registered: {addr} → {_eth_did(addr)}")

        return {
            "address": addr,
            "did": _eth_did(addr),
            "display_name": wallet_data["display_name"],
            "created_at": wallet_data["created_at"],
            "already_existed": False,
        }

    def get_wallet_summary(self, eth_address: str) -> dict | None:
        wallet = get_wallet(_normalize(eth_address))
        if not wallet:
            return None
        return {
            "address": wallet["address"],
            "did": wallet["did"],
            "display_name": wallet.get("display_name", ""),
            "created_at": wallet["created_at"],
            "credential_count": len(wallet.get("credentials", [])),
            "pending_offer_count": len(wallet.get("pending_offers", [])),
        }

    # ── Credential Offer (Issuer → Wallet) ────────────────────────────────────

    def offer_credential(self, eth_address: str, credential: dict) -> dict:
        """
        Municipality sends a VC offer to the citizen's wallet.
        The citizen must explicitly accept before the VC is stored.
        """
        addr = _normalize(eth_address)
        offer_id = str(uuid.uuid4())
        license_id = credential.get("credentialSubject", {}).get("licenseId", "unknown")

        offer = {
            "offer_id": offer_id,
            "license_id": license_id,
            "credential": credential,
            "issuer_name": credential.get("issuer", {}).get("name", "Unknown Authority"),
            "offered_at": datetime.now().isoformat() + "Z",
        }

        if not add_pending_offer(addr, offer):
            # Wallet not registered yet — auto-register
            self.register_wallet(addr)
            add_pending_offer(addr, offer)

        print(f"   [Wallet] Offer sent to {addr}: license={license_id}")
        return {"offer_id": offer_id, "license_id": license_id}

    def list_offers(self, eth_address: str) -> list:
        offers = get_pending_offers(_normalize(eth_address))
        return [
            {
                "offer_id": o["offer_id"],
                "license_id": o["license_id"],
                "issuer_name": o.get("issuer_name", "Unknown"),
                "offered_at": o["offered_at"],
            }
            for o in offers
        ]

    def accept_offer(self, eth_address: str, offer_id: str) -> dict:
        """Citizen accepts an offer → VC moved from pending to accepted credentials."""
        result = accept_pending_offer(_normalize(eth_address), offer_id)
        if not result:
            raise ValueError(f"Offer {offer_id} not found or already accepted.")
        print(f"   [Wallet] Offer {offer_id} accepted by {eth_address[:10]}…")
        return {"accepted": True, "license_id": result["license_id"]}

    # ── Challenge Generation (step 1 of VP flow) ──────────────────────────────

    def create_challenge(self, eth_address: str, license_id: str) -> dict:
        """
        Generate a one-time challenge string for MetaMask to sign.
        The challenge expires in 5 minutes and can only be used once.
        """
        addr = _normalize(eth_address)
        credential = get_credential(addr, license_id)
        if not credential:
            raise ValueError(f"Credential {license_id} not found in wallet {addr}")

        challenge_id = str(uuid.uuid4())
        expires_at = (datetime.now() + timedelta(minutes=5)).isoformat() + "Z"

        # Human-readable message — MetaMask shows this to the user before signing
        challenge_text = (
            f"E-Ruhsat License Presentation\n\n"
            f"License ID: {license_id}\n"
            f"Holder: {addr}\n"
            f"Challenge: {challenge_id}\n"
            f"Expires: {expires_at}\n\n"
            f"By signing this message you authorize a one-time\n"
            f"presentation of your license to an inspector.\n"
            f"This signature cannot be reused."
        )

        store_challenge(challenge_id, {
            "eth_address": addr,
            "license_id": license_id,
            "challenge_text": challenge_text,
            "expires_at": expires_at,
        })

        print(f"   [Wallet] Challenge created for {license_id}, id={challenge_id[:8]}…")
        return {
            "challenge_id": challenge_id,
            "challenge_text": challenge_text,
            "expires_at": expires_at,
        }

    # ── Verify Presentation (step 2 — after MetaMask signs) ───────────────────

    def verify_presentation(
        self,
        challenge_id: str,
        eth_address: str,
        signature: str,
    ) -> dict:
        """
        Verify a MetaMask-signed Verifiable Presentation.

        Checks:
          1. Challenge exists and has not been used before (anti-replay)
          2. Challenge has not expired
          3. Recovered signer matches the claimed holder address
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

        # 3. Recover signer from MetaMask signature
        addr = _normalize(eth_address)
        try:
            recovered = _recover_signer(challenge["challenge_text"], signature)
        except Exception as exc:
            return {
                "valid": False,
                "reason": "signature_error",
                "message": f"Could not parse signature: {exc}",
            }

        if recovered != addr:
            return {
                "valid": False,
                "reason": "signer_mismatch",
                "message": (
                    f"Signature was made by {recovered}, "
                    f"but the credential belongs to {addr}."
                ),
            }

        # 4 & 5. Verify the embedded VC (issuer signature + expiry)
        credential = get_credential(addr, challenge["license_id"])
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
            "message": "License verified successfully via MetaMask wallet.",
            "holder_address": addr,
            "holder_did": _eth_did(addr),
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

    def list_credentials(self, eth_address: str) -> list:
        creds = get_credentials(_normalize(eth_address))
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