"""
Encrypted license ledger with business-rule enforcement.
Compatible with LicenseIssuer and /api/contract/stats.
"""
import os
import json
import hashlib
import base64
from datetime import datetime
from typing import Dict, Any, Optional

import config
from cities import all_issuer_dids, get_city
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class LicenseContract:
    def __init__(self, city_slug: str | None = None):
        self.city_slug = config.resolve_city_slug(city_slug=city_slug)
        self.city = get_city(self.city_slug)
        paths = config.paths_for_city(self.city_slug)

        self.ledger_path = paths["data_dir"] / "contract_ledger.json"
        self.state_path = paths["data_dir"] / "contract_state.json"
        self.credentials_path = paths["data_dir"] / "contract_credentials.json"
        self.keys_dir = paths["keys_dir"]

        self._ensure_database_exists()
        self._ensure_keys_exist()
        self.state: Dict[str, dict] = self._load_state()

    def _ensure_database_exists(self):
        for path in [self.ledger_path, self.credentials_path]:
            if not path.exists():
                with open(path, "w", encoding="utf-8") as file:
                    json.dump({}, file)

    def _ensure_keys_exist(self):
        os.makedirs(self.keys_dir, exist_ok=True)
        priv_path = self.keys_dir / "issuer_private_key.pem"
        pub_path = self.keys_dir / "issuer_public_key.pem"

        if not priv_path.exists() or not pub_path.exists():
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public_key = private_key.public_key()

            with open(priv_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ))
            with open(pub_path, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                ))

    def _load_private_key(self):
        with open(self.keys_dir / "issuer_private_key.pem", "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    def _load_public_key(self):
        with open(self.keys_dir / "issuer_public_key.pem", "rb") as f:
            return serialization.load_pem_public_key(f.read())

    def _hybrid_encrypt(self, plain_text: str) -> Dict[str, str]:
        public_key = self._load_public_key()
        aes_key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(12)
        encrypted_data = aesgcm.encrypt(nonce, plain_text.encode("utf-8"), None)
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return {
            "encrypted_payload": base64.b64encode(encrypted_data).decode("utf-8"),
            "encrypted_key": base64.b64encode(encrypted_aes_key).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8"),
        }

    def _hybrid_decrypt(self, cipher_package: Dict[str, str]) -> str:
        private_key = self._load_private_key()
        encrypted_data = base64.b64decode(cipher_package["encrypted_payload"])
        encrypted_aes_key = base64.b64decode(cipher_package["encrypted_key"])
        nonce = base64.b64decode(cipher_package["nonce"])
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        aesgcm = AESGCM(aes_key)
        return aesgcm.decrypt(nonce, encrypted_data, None).decode("utf-8")

    def _load_json(self, path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}

    def _save_json(self, path, data: Dict[str, Any]):
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def _load_state(self) -> dict:
        state = self._load_json(self.state_path)
        if not state:
            return {}
        first = next(iter(state.values()), None)
        if isinstance(first, str):
            return {}
        return state

    def _save_state(self):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def _calculate_merkle_root(self, data_block: Dict[str, Any]) -> str:
        serialized_data = json.dumps(data_block, sort_keys=True)
        return hashlib.sha256(serialized_data.encode("utf-8")).hexdigest()

    def _is_authorized_issuer(self, issuer_did: str) -> bool:
        authorized = set(all_issuer_dids())
        authorized.add(self.city["issuer_did"])
        return issuer_did in authorized

    def _license_exists(self, license_id: str) -> bool:
        return license_id in self.state

    def _validate_issue_rules(self, license_data: dict, issuer_did: str) -> Optional[dict]:
        if not self._is_authorized_issuer(issuer_did):
            return {
                "success": False,
                "error": "UNAUTHORIZED_ISSUER",
                "message": f"Issuer {issuer_did} is not authorized to issue licenses",
            }

        license_id = license_data.get("license_id")
        if not license_id:
            return {
                "success": False,
                "error": "MISSING_LICENSE_ID",
                "message": "License number is required",
            }

        if self._license_exists(license_id):
            return {
                "success": False,
                "error": "DUPLICATE_LICENSE",
                "message": f"License {license_id} is already registered in the system",
            }

        issue_date_str = license_data.get("issue_date")
        expiry_date_str = license_data.get("expiry_date")
        if not issue_date_str or not expiry_date_str:
            return {
                "success": False,
                "error": "MISSING_DATES",
                "message": "Issue and expiry dates are required",
            }

        try:
            issue_date = datetime.fromisoformat(issue_date_str[:10])
            expiry_date = datetime.fromisoformat(expiry_date_str[:10])
        except ValueError:
            return {
                "success": False,
                "error": "INVALID_DATE_FORMAT",
                "message": "Invalid date format (use YYYY-MM-DD)",
            }

        if expiry_date <= issue_date:
            return {
                "success": False,
                "error": "INVALID_DATES",
                "message": "Expiry date must be after the issue date",
            }

        required_fields = ["license_type", "owner_name", "citizen_id", "region"]
        missing = [f for f in required_fields if not license_data.get(f)]
        if missing:
            return {
                "success": False,
                "error": "MISSING_FIELDS",
                "message": f"Missing fields: {', '.join(missing)}",
            }

        citizen_id = str(license_data.get("citizen_id", ""))
        if not citizen_id.isdigit() or len(citizen_id) != 11:
            return {
                "success": False,
                "error": "INVALID_CITIZEN_ID",
                "message": "National ID must be exactly 11 digits",
            }

        return None

    def _to_contract_payload(self, license_data: dict) -> Dict[str, Any]:
        return {
            "license_id": license_data["license_id"],
            "holder_name": license_data.get("owner_name", license_data.get("holder_name", "")),
            "business_name": license_data.get("business_name", ""),
            "address": license_data.get("address", ""),
            "license_type": license_data["license_type"],
            "issue_date": license_data["issue_date"],
        }

    def issue_license(self, license_data: dict, issuer_did: str) -> dict:
        """Validate business rules, persist encrypted ledger entry, update state."""
        failure = self._validate_issue_rules(license_data, issuer_did)
        if failure:
            return failure

        license_id = license_data["license_id"]
        contract_payload = self._to_contract_payload(license_data)
        state_hash = self._calculate_merkle_root(contract_payload)

        sensitive_subject_data = {
            "holderName": contract_payload["holder_name"],
            "businessName": contract_payload["business_name"],
            "address": contract_payload["address"],
            "licenseType": contract_payload["license_type"],
            "citizenId": license_data.get("citizen_id", ""),
            "region": license_data.get("region", ""),
        }
        encrypted_package = self._hybrid_encrypt(json.dumps(sensitive_subject_data))

        ledger = self._load_json(self.ledger_path)
        credentials = self._load_json(self.credentials_path)

        credentials[license_id] = {
            "context": "https://www.w3.org/2018/credentials/v1",
            "type": ["VerifiableCredential", "EncryptedBusinessLicenseCredential"],
            "credentialSubject": {
                "id": f"did:indy:tr:{self.city_slug}:{license_id}",
                "encryptedData": encrypted_package,
            },
            "issuanceDate": license_data["issue_date"],
        }

        ledger[license_id] = {
            "block_height": len(ledger) + 1,
            "state_hash": state_hash,
            "previous_hash": list(ledger.values())[-1]["state_hash"] if ledger else "0" * 64,
            "tx_timestamp": license_data["issue_date"],
        }

        self.state[license_id] = {
            **license_data,
            "status": "ACTIVE",
            "issuer": issuer_did,
            "issued_at": datetime.now().isoformat(),
            "revoked": False,
            "contract_version": "2.0",
            "state_hash": state_hash,
            "encryption_applied": "RSA-2048/AES-GCM-256",
        }

        self._save_json(self.ledger_path, ledger)
        self._save_json(self.credentials_path, credentials)
        self._save_state()

        print(f"   Smart Contract: License {license_id} issued (encrypted)")

        return {
            "success": True,
            "license_id": license_id,
            "message": "License created successfully (all rules passed)",
            "block_height": ledger[license_id]["block_height"],
            "state_hash": state_hash,
            "encryption_applied": "RSA-2048/AES-GCM-256",
        }

    def revoke_license(self, license_id: str, issuer_did: str, reason: str) -> dict:
        if not self._license_exists(license_id):
            return {
                "success": False,
                "error": "LICENSE_NOT_FOUND",
                "message": f"License {license_id} not found",
            }

        record = self.state[license_id]
        if record.get("revoked"):
            return {
                "success": False,
                "error": "ALREADY_REVOKED",
                "message": f"License {license_id} is already revoked",
            }

        if record.get("issuer") != issuer_did:
            return {
                "success": False,
                "error": "UNAUTHORIZED_REVOKE",
                "message": "Only the issuing authority can revoke this license",
            }

        if not reason or len(reason.strip()) < 5:
            return {
                "success": False,
                "error": "INVALID_REASON",
                "message": "Revocation reason must be at least 5 characters",
            }

        record["revoked"] = True
        record["revoked_at"] = datetime.now().isoformat()
        record["revoke_reason"] = reason
        record["status"] = "REVOKED"
        self._save_state()

        print(f"   Smart Contract: License {license_id} revoked")
        return {
            "success": True,
            "license_id": license_id,
            "message": "License revoked",
        }

    def verify_license(self, license_id: str) -> dict:
        ledger = self._load_json(self.ledger_path)
        credentials = self._load_json(self.credentials_path)

        if license_id not in self.state:
            return {
                "valid": False,
                "status": "NOT_FOUND",
                "message": "License not found in the system",
            }

        record = self.state[license_id]
        if record.get("revoked"):
            return {
                "valid": False,
                "status": "REVOKED",
                "message": "License has been revoked",
                "revoked_at": record.get("revoked_at"),
                "reason": record.get("revoke_reason"),
            }

        expiry_date_str = record.get("expiry_date")
        if expiry_date_str:
            try:
                expiry_date = datetime.fromisoformat(expiry_date_str[:10])
                if datetime.now() > expiry_date:
                    return {
                        "valid": False,
                        "status": "EXPIRED",
                        "message": "License has expired",
                        "expiry_date": expiry_date_str,
                    }
            except ValueError:
                pass

        crypto_valid = False
        crypto_details = {}
        if license_id in ledger and license_id in credentials:
            try:
                vc = credentials[license_id]
                encrypted_package = vc["credentialSubject"]["encryptedData"]
                decrypted_subject_str = self._hybrid_decrypt(encrypted_package)
                subject = json.loads(decrypted_subject_str)
                reconstructed_payload = {
                    "license_id": license_id,
                    "holder_name": subject["holderName"],
                    "business_name": subject["businessName"],
                    "address": subject["address"],
                    "license_type": subject["licenseType"],
                    "issue_date": vc["issuanceDate"],
                }
                current_hash = self._calculate_merkle_root(reconstructed_payload)
                original_hash = ledger[license_id]["state_hash"]
                crypto_valid = current_hash == original_hash
                crypto_details = {
                    "cryptographic_match": crypto_valid,
                    "decryption_status": "SUCCESSFUL",
                }
            except Exception as exc:
                crypto_details = {
                    "cryptographic_match": False,
                    "decryption_status": f"FAILED: {exc}",
                }

        is_active = record.get("status") == "ACTIVE"
        is_valid = is_active and (crypto_valid if crypto_details else True)

        return {
            "valid": is_valid,
            "status": record.get("status", "UNKNOWN"),
            "message": "License is valid" if is_valid else "License could not be verified",
            "data": record,
            "verification_details": crypto_details,
        }

    def get_license_count(self) -> dict:
        active = sum(
            1 for lic in self.state.values()
            if lic.get("status") == "ACTIVE" and not lic.get("revoked")
        )
        revoked = sum(1 for lic in self.state.values() if lic.get("revoked"))
        return {
            "total": len(self.state),
            "active": active,
            "revoked": revoked,
        }

    def get_all_licenses(self) -> list:
        return list(self.state.values())
