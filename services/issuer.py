"""Issuer service — issues digital licenses for any Turkish municipality."""
import json
from datetime import datetime

import config
from cities import get_city
from contracts.license_contract import LicenseContract
from utils.blockchain_logger import BlockchainLogger
from utils.crypto import CryptoManager
from utils.ipfs_manager import IPFSManager
from utils.qr_generator import QRCodeManager
from utils.verifiable_credentials import VerifiableCredentialManager


class LicenseIssuer:
    """Issue digital licenses with QR codes and IPFS storage."""

    def __init__(self):
        self.ipfs = IPFSManager()
        print("   License Issuer initialized (multi-city Turkey)")

    def issue_license(
        self,
        license_data: dict,
        pdf_path: str | None = None,
        city_slug: str | None = None,
    ) -> dict:
        city_slug = config.resolve_city_slug(
            license_id=license_data.get("license_id"),
            city_slug=city_slug or license_data.get("city_slug"),
        )
        city = get_city(city_slug)
        paths = config.paths_for_city(city_slug)

        license_data["city_slug"] = city_slug
        license_data["city_name"] = city["name"]
        license_data["authority"] = city["issuer_name"]

        print(f"\n--- ISSUING LICENSE [{city['name']}]: {license_data['license_id']} ---")

        contract = LicenseContract(city_slug)
        contract_result = contract.issue_license(license_data, city["issuer_did"])
        if not contract_result["success"]:
            print(f"   Smart Contract rejected: {contract_result['message']}")
            raise Exception(f"Smart Contract: {contract_result['message']}")

        if pdf_path:
            ipfs_data = self.ipfs.upload_encrypted_document(
                pdf_path,
                license_data["license_id"],
            )
            license_data["ipfs_hash"] = ipfs_data["ipfs_hash"]
            license_data["document_hash"] = ipfs_data["document_hash"]

        vc_manager = VerifiableCredentialManager(city_slug)
        credential = vc_manager.create_credential(license_data)

        qr_path = QRCodeManager.generate_qr_code(
            credential,
            license_data["license_id"],
            city,
            paths["qr_codes_dir"],
        )

        blockchain = BlockchainLogger(city_slug)
        blockchain.add_block(
            {
                "action": "ISSUE_LICENSE",
                "city_slug": city_slug,
                "credential": credential,
                "ipfs_hash": license_data.get("ipfs_hash", ""),
            }
        )

        license_data["verifiable_credential"] = credential
        self._save_to_db(license_data, qr_path, paths["credentials"])

        return {
            "success": True,
            "city_slug": city_slug,
            "city_name": city["name"],
            "ipfs_hash": license_data.get("ipfs_hash"),
            "qr_url": f"/data/{city_slug}/qr_codes/{license_data['license_id']}.png",
            "credential": credential,
        }

    def _save_to_db(self, data: dict, qr_path: str, db_path):
        db = []
        if db_path.exists():
            try:
                with open(db_path, "r", encoding="utf-8") as file:
                    db = json.load(file)
            except json.JSONDecodeError:
                db = []

        data["created_at"] = datetime.now().isoformat()
        data["qr_url"] = qr_path
        db.append(data)

        with open(db_path, "w", encoding="utf-8") as file:
            json.dump(db, file, indent=2, ensure_ascii=False)

        print(f"   Saved to database: {data['license_id']} ({data['city_slug']})")

    def get_license_info(self, license_id: str, city_slug: str | None = None):
        """Find a license in the matching city datastore."""
        if city_slug:
            return self._load_from_city(license_id, city_slug)

        primary = config.resolve_city_slug(license_id=license_id)
        found = self._load_from_city(license_id, primary)
        if found or not config.MULTI_CITY_ENABLED:
            return found
        return self._search_all_cities(license_id, skip_slug=primary)

    def _load_from_city(self, license_id: str, city_slug: str):
        db_path = config.paths_for_city(city_slug)["credentials"]
        if not db_path.exists():
            return None
        try:
            with open(db_path, "r", encoding="utf-8") as file:
                db = json.load(file)
            for item in db:
                if str(item.get("license_id", "")).strip() == str(license_id).strip():
                    return item
        except Exception as exc:
            print(f"   Database error ({city_slug}): {exc}")
        return None

    def _search_all_cities(self, license_id: str, skip_slug: str | None = None):
        from cities import CITIES

        for slug in CITIES:
            if slug == skip_slug:
                continue
            found = self._load_from_city(license_id, slug)
            if found:
                return found
        return None

    def list_licenses(self, city_slug: str | None = None) -> list:
        slug = config.resolve_city_slug(city_slug=city_slug)
        db_path = config.paths_for_city(slug)["credentials"]
        if not db_path.exists():
            return []
        with open(db_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def contract_stats(self, city_slug: str | None = None) -> dict:
        slug = config.resolve_city_slug(city_slug=city_slug)
        return LicenseContract(slug).get_license_count()
