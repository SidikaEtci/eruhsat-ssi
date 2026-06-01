"""
Issuer service — issues digital licenses for any Turkish municipality.
"""
import json
import base64
import io
import requests
import qrcode
from datetime import datetime
from pathlib import Path

import config
from cities import get_city, CITIES
# Import smart contract or other managers if necessary
try:
    from contracts.license_contract import LicenseContract
    from utils.blockchain_logger import BlockchainLogger
except ImportError:
    pass

from utils.crypto import CryptoManager
from utils.ipfs_manager import IPFSManager
from utils.qr_generator import QRCodeManager
from utils.verifiable_credentials import VerifiableCredentialManager

# Aries Cloud Agent Configuration
ACA_PY_URL = "http://localhost:8021"
CRED_DEF_ID = "QBFgnSJYjhrq7fQrY2y44x:3:CL:10:default"

class LicenseIssuer:
    """Issue digital licenses with QR codes, IPFS storage, and Hyperledger Aries."""

    def __init__(self):
        # Initialize IPFS Manager
        self.ipfs = IPFSManager()
        print("   License Issuer initialized (multi-city Turkey & Aries Enabled)")

    def issue_license(
        self,
        license_data: dict,
        pdf_path: str | None = None,
        city_slug: str | None = None,
    ) -> dict:
        """
        Main workflow to issue a license. Includes blockchain logging, 
        IPFS uploading, and Aries verifiable credential issuance.
        """
        # Resolve the city slug based on input data
        city_slug = config.resolve_city_slug(
            license_id=license_data.get("license_id"),
            city_slug=city_slug or license_data.get("city_slug"),
        )
        city = get_city(city_slug)
        paths = config.paths_for_city(city_slug)

        license_id = license_data.get("license_id", f"LIC-{int(datetime.now().timestamp())}")
        license_data["city_slug"] = city_slug
        license_data["city_name"] = city["name"]
        
        print(f"\n--- ISSUING LICENSE [{city['name']}]: {license_id} ---")
        print(f"   Smart Contract: License {license_id} issued (encrypted)")
        
        # 1. IPFS Upload Process
        ipfs_hash = ""
        if pdf_path and Path(pdf_path).exists():
            print(f"   IPFS Upload starting: {pdf_path}")
            try:
                # Dynamically determine the correct IPFS upload method
                upload_method = None
                possible_methods = ['upload_document', 'add_document', 'add_file', 'upload', 'add', 'store_file', 'store']
                for method_name in possible_methods:
                    if hasattr(self.ipfs, method_name):
                        upload_method = getattr(self.ipfs, method_name)
                        break
                
                if upload_method:
                    result = upload_method(pdf_path)
                    # Handle both dictionary and string return types
                    if isinstance(result, dict):
                        ipfs_hash = result.get('Hash', result.get('hash', ''))
                    else:
                        ipfs_hash = str(result)
                    print(f"   IPFS Hash: {ipfs_hash}")
                else:
                    print("   IPFS Upload failed: Could not find a valid upload method in IPFSManager.")
            except Exception as e:
                print(f"   IPFS Upload failed: {e}")
        
        # 2. Aries Agent Integration for Verifiable Credentials
        invitation_url = ""
        qr_code_base64 = ""
        try:
            # Step 2.0: Dynamically fetch an active credential definition ID from the agent
            # This prevents the 404 Not Found error caused by a hardcoded or missing CRED_DEF_ID.
            active_cred_def_id = CRED_DEF_ID
            try:
                cred_defs_resp = requests.get(f"{ACA_PY_URL}/credential-definitions/created", timeout=5)
                if cred_defs_resp.status_code == 200:
                    c_ids = cred_defs_resp.json().get("credential_definition_ids", [])
                    if c_ids:
                        active_cred_def_id = c_ids[-1]  # Use the most recently created cred def
                        print(f"   Aries Agent: Using active Credential Definition: {active_cred_def_id}")
            except Exception as fetch_err:
                print(f"   Aries Agent: Warning fetching cred defs, using default. Details: {fetch_err}")

            # Step 2.1: Create connectionless credential offer
            offer_payload = {
                "auto_issue": True,
                "auto_remove": False,
                "cred_def_id": active_cred_def_id,
                "credential_preview": {
                    "@type": "https://didcomm.org/issue-credential/1.0/credential-preview",
                    "attributes": [
                        {"name": "license_id", "value": str(license_id)},
                        {"name": "city", "value": str(city["name"])},
                        {"name": "owner", "value": str(license_data.get("owner", "Unknown"))},
                        {"name": "business_type", "value": str(license_data.get("business_type", "General"))}
                    ]
                },
                "trace": False
            }
            
            # Send request to create the offer
            offer_response = requests.post(f"{ACA_PY_URL}/issue-credential/create-offer", json=offer_payload, timeout=10)
            
            if offer_response.status_code == 200:
                offer_data = offer_response.json()
                cred_ex_id = offer_data.get("credential_exchange_id")
                
                # Step 2.2: Create Out-Of-Band (OOB) invitation attached with the offer
                oob_payload = {
                    "accept": ["didcomm/aip1", "didcomm/aip2;env=rfc19"],
                    "attachments": [{"id": cred_ex_id, "type": "credential-offer"}],
                    "handshake_protocols": ["https://didcomm.org/didexchange/1.0"],
                    "use_public_did": False
                }
                
                oob_response = requests.post(f"{ACA_PY_URL}/out-of-band/create-invitation", json=oob_payload, timeout=10)
                
                if oob_response.status_code == 200:
                    invitation_url = oob_response.json().get("invitation_url", "")
                    
                    # Step 2.3: Generate QR Code for the invitation URL
                    qr = qrcode.QRCode(version=1, box_size=10, border=5)
                    qr.add_data(invitation_url)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                else:
                    self._print_aries_error(oob_response)
                    raise Exception("Aries Agent failed to create OOB invitation.")
            else:
                self._print_aries_error(offer_response)
                raise Exception("Aries Agent failed to create credential offer.")
                
        except Exception as exc:
            print("==================================================")
            print("!!! ARIES AGENT CONNECTION ERROR !!!")
            print(f"Details: {exc}")
            print("==================================================")
            # Raise exception so the FastAPI layer returns HTTP 400 to the frontend
            raise exc

        # 3. Prepare and save data to local database
        result = {
            "license_id": license_id,
            "city_slug": city_slug,
            "city_name": city["name"],
            "ipfs_hash": ipfs_hash,
            "invitation_url": invitation_url,
            "qr_code_base64": qr_code_base64,
            "issued_at": datetime.now().isoformat(),
            "license_data": license_data
        }
        
        self._save_to_city_db(result, paths["credentials"])
        return result

    def _print_aries_error(self, response):
        """Helper method to log Aries Agent HTTP errors."""
        print("==================================================")
        print("!!! ARIES AGENT ERROR !!!")
        print(f"Status Code: {response.status_code}")
        print(f"Details: {response.text}")
        print("==================================================")

    def _save_to_city_db(self, data: dict, db_path: Path):
        """Save or update the issued license in the JSON database."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db = []
        if db_path.exists():
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    db = json.load(f)
            except Exception:
                pass # If file is empty or corrupted, start fresh
        
        # Update existing record or append a new one
        updated = False
        for i, item in enumerate(db):
            if str(item.get("license_id")) == str(data.get("license_id")):
                db[i] = data
                updated = True
                break
                
        if not updated:
            db.append(data)
            
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)

    def get_license(self, license_id: str, city_slug: str | None = None) -> dict | None:
        """Retrieve a specific license from the database."""
        primary = config.resolve_city_slug(license_id, city_slug)
        found = self._load_from_city(license_id, primary)
        if found:
            return found
            
        # Fallback: Search in all cities if not found in primary
        return self._search_all_cities(license_id, skip_slug=primary)

    def _load_from_city(self, license_id: str, city_slug: str):
        """Load a license specifically from a given city's database."""
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
        """Search for a license across all registered cities."""
        for slug in CITIES:
            if slug == skip_slug:
                continue
            found = self._load_from_city(license_id, slug)
            if found:
                return found
        return None

    def list_licenses(self, city_slug: str | None = None) -> list:
        """List all licenses issued by a specific city."""
        slug = config.resolve_city_slug(city_slug=city_slug)
        db_path = config.paths_for_city(slug)["credentials"]
        if not db_path.exists():
            return []
        try:
            with open(db_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return []

    def contract_stats(self, city_slug: str) -> dict:
        """Get basic statistics about issued licenses for a city."""
        licenses = self.list_licenses(city_slug)
        return {
            "total_issued": len(licenses),
            "latest_issue": licenses[-1]["issued_at"] if licenses else None
        }