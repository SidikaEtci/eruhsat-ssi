"""
W3C Verifiable Credentials for Turkish municipal e-licenses.
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import config
from cities import get_city
from utils.crypto import CryptoManager


class VerifiableCredentialManager:
    """Creates and verifies W3C Verifiable Credentials per municipality."""

    def __init__(self, city_slug: str | None = None):
        self.city_slug = config.resolve_city_slug(city_slug=city_slug)
        self.city = get_city(self.city_slug)
        self.private_key, self.public_key = CryptoManager.generate_keypair(
            seed=self.city["issuer_seed"]
        )
        self.issuer_did = self.city["issuer_did"]

    def create_credential(self, license_data: dict) -> dict:
        holder_did = self._create_holder_did(license_data["citizen_id"])

        credential_subject = {
            "id": holder_did,
            "licenseId": license_data["license_id"],
            "licenseType": license_data["license_type"],
            "businessName": license_data.get("business_name"),
            "city": self.city["name"],
            "citySlug": self.city_slug,
            "region": license_data["region"],
            "address": license_data.get("address"),
            "validFrom": license_data["issue_date"],
            "validUntil": license_data["expiry_date"],
        }

        credential = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                self.city["credential_context"],
            ],
            "type": ["VerifiableCredential", "LicenseCredential"],
            "issuer": {
                "id": self.issuer_did,
                "name": self.city["issuer_name"],
            },
            "issuanceDate": datetime.now().isoformat() + "Z",
            "expirationDate": (datetime.now() + timedelta(days=365)).isoformat() + "Z",
            "credentialSubject": credential_subject,
        }
        credential["proof"] = self._create_proof(credential)
        return credential

    def _create_holder_did(self, citizen_id: str) -> str:
        hashed = hashlib.sha256(citizen_id.encode()).hexdigest()[:16]
        return f"did:indy:tr:{self.city_slug}:{hashed}"

    def _create_proof(self, credential: dict) -> dict:
        canonical = json.dumps(credential, sort_keys=True, ensure_ascii=False)
        signature = CryptoManager.sign_data(canonical, self.private_key)
        return {
            "type": "Ed25519Signature2020",
            "created": datetime.now().isoformat() + "Z",
            "verificationMethod": f"{self.issuer_did}#keys-1",
            "proofPurpose": "assertionMethod",
            "proofValue": signature,
        }

    def verify_credential(self, credential: dict) -> Tuple[bool, str]:
        try:
            proof = credential.get("proof")
            if not proof:
                return False, "No proof found"

            credential_copy = credential.copy()
            del credential_copy["proof"]
            canonical = json.dumps(credential_copy, sort_keys=True, ensure_ascii=False)

            if not CryptoManager.verify_signature(
                canonical, proof["proofValue"], self.public_key
            ):
                return False, "Invalid signature"

            expiration = credential.get("expirationDate")
            if expiration:
                exp_date = datetime.fromisoformat(expiration.replace("Z", ""))
                if datetime.now() > exp_date:
                    return False, "Credential expired"

            return True, "Credential valid"
        except Exception as exc:
            return False, f"Verification error: {exc}"

    def create_presentation(
        self, credential: dict, disclosed_attributes: List[str]
    ) -> dict:
        full_subject = credential["credentialSubject"]
        disclosed_subject = {
            key: value
            for key, value in full_subject.items()
            if key in disclosed_attributes or key == "id"
        }

        presentation = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiablePresentation"],
            "verifiableCredential": [{**credential, "credentialSubject": disclosed_subject}],
            "holder": full_subject["id"],
        }
        presentation["proof"] = self._create_presentation_proof(presentation)
        return presentation

    def _create_presentation_proof(self, presentation: dict) -> dict:
        canonical = json.dumps(presentation, sort_keys=True, ensure_ascii=False)
        signature = CryptoManager.sign_data(canonical, self.private_key)
        return {
            "type": "Ed25519Signature2020",
            "created": datetime.now().isoformat() + "Z",
            "verificationMethod": f"{self.issuer_did}#keys-1",
            "proofPurpose": "authentication",
            "challenge": hashlib.sha256(str(datetime.now()).encode()).hexdigest(),
            "proofValue": signature,
        }
