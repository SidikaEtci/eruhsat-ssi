"""
Smart Contract for License Management
Enforces business rules automatically
"""
from datetime import datetime
from typing import Dict, Optional
import json
from pathlib import Path
import config


class LicenseSmartContract:
    """
    Smart Contract - Business Rules Enforcer
    
    Rules:
    1. Only authorized issuers can issue licenses
    2. License ID must be unique
    3. Expiry date must be after issue date
    4. All required fields must be present
    5. Cannot revoke already revoked licenses
    6. Only issuer can revoke their own licenses
    """
    
    def __init__(self):
        self.state_file = config.DATA_DIR / "contract_state.json"
        self.state: Dict[str, dict] = self._load_state()
    
    def _load_state(self) -> dict:
        """Load contract state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_state(self):
        """Save contract state to file"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def issue_license(self, license_data: dict, issuer_did: str) -> dict:
        """
        Execute: Issue License
        
        Enforces business rules before allowing issuance
        
        Returns:
            {"success": True, "message": "..."} if successful
            {"success": False, "error": "...", "message": "..."} if failed
        """
        
        # RULE 1: Check issuer authorization
        if not self._is_authorized_issuer(issuer_did):
            return {
                "success": False,
                "error": "UNAUTHORIZED_ISSUER",
                "message": f"Issuer {issuer_did} ruhsat vermeye yetkili değil"
            }
        
        # RULE 2: Check duplicate license ID
        license_id = license_data.get("license_id")
        if not license_id:
            return {
                "success": False,
                "error": "MISSING_LICENSE_ID",
                "message": "Ruhsat numarası gerekli"
            }
        
        if self._license_exists(license_id):
            return {
                "success": False,
                "error": "DUPLICATE_LICENSE",
                "message": f"Ruhsat {license_id} zaten sistemde kayıtlı"
            }
        
        # RULE 3: Validate dates
        issue_date_str = license_data.get("issue_date")
        expiry_date_str = license_data.get("expiry_date")
        
        if not issue_date_str or not expiry_date_str:
            return {
                "success": False,
                "error": "MISSING_DATES",
                "message": "Verilme ve geçerlilik tarihleri gerekli"
            }
        
        try:
            issue_date = datetime.fromisoformat(issue_date_str)
            expiry_date = datetime.fromisoformat(expiry_date_str)
        except:
            return {
                "success": False,
                "error": "INVALID_DATE_FORMAT",
                "message": "Tarih formatı hatalı (YYYY-MM-DD olmalı)"
            }
        
        if expiry_date <= issue_date:
            return {
                "success": False,
                "error": "INVALID_DATES",
                "message": "Geçerlilik tarihi, düzenlenme tarihinden sonra olmalı"
            }
        
        # RULE 4: Required fields check
        required_fields = ["license_type", "owner_name", "citizen_id", "region"]
        missing = [f for f in required_fields if not license_data.get(f)]
        
        if missing:
            return {
                "success": False,
                "error": "MISSING_FIELDS",
                "message": f"Eksik alanlar: {', '.join(missing)}"
            }
        
        # RULE 5: Validate TC Kimlik (11 digits)
        citizen_id = license_data.get("citizen_id", "")
        if not citizen_id.isdigit() or len(citizen_id) != 11:
            return {
                "success": False,
                "error": "INVALID_CITIZEN_ID",
                "message": "TC Kimlik numarası 11 haneli olmalı"
            }
        
        # ALL RULES PASSED - Execute contract
        self.state[license_id] = {
            **license_data,
            "status": "ACTIVE",
            "issuer": issuer_did,
            "issued_at": datetime.now().isoformat(),
            "revoked": False,
            "contract_version": "1.0"
        }
        
        self._save_state()
        
        print(f"✅ Smart Contract: License {license_id} issued")
        
        return {
            "success": True,
            "license_id": license_id,
            "message": "Ruhsat başarıyla oluşturuldu (tüm kurallar geçildi)"
        }
    
    def revoke_license(self, license_id: str, issuer_did: str, reason: str) -> dict:
        """
        Execute: Revoke License
        
        Enforces revocation rules
        """
        
        # RULE 1: License must exist
        if not self._license_exists(license_id):
            return {
                "success": False,
                "error": "LICENSE_NOT_FOUND",
                "message": f"Ruhsat {license_id} bulunamadı"
            }
        
        license_data = self.state[license_id]
        
        # RULE 2: Cannot revoke already revoked license
        if license_data.get("revoked"):
            return {
                "success": False,
                "error": "ALREADY_REVOKED",
                "message": f"Ruhsat {license_id} zaten iptal edilmiş"
            }
        
        # RULE 3: Only issuer can revoke
        if license_data["issuer"] != issuer_did:
            return {
                "success": False,
                "error": "UNAUTHORIZED_REVOKE",
                "message": "Sadece ruhsatı veren kurum iptal edebilir"
            }
        
        # RULE 4: Reason is required
        if not reason or len(reason.strip()) < 5:
            return {
                "success": False,
                "error": "INVALID_REASON",
                "message": "İptal nedeni en az 5 karakter olmalı"
            }
        
        # ALL RULES PASSED - Execute revocation
        self.state[license_id]["revoked"] = True
        self.state[license_id]["revoked_at"] = datetime.now().isoformat()
        self.state[license_id]["revoke_reason"] = reason
        self.state[license_id]["status"] = "REVOKED"
        
        self._save_state()
        
        print(f"✅ Smart Contract: License {license_id} revoked")
        
        return {
            "success": True,
            "license_id": license_id,
            "message": "Ruhsat iptal edildi"
        }
    
    def verify_license(self, license_id: str) -> dict:
        """
        Query: Verify License Status
        
        Returns current state of license
        """
        if not self._license_exists(license_id):
            return {
                "valid": False,
                "status": "NOT_FOUND",
                "message": "Ruhsat sistemde bulunamadı"
            }
        
        license_data = self.state[license_id]
        
        # Check revoked
        if license_data.get("revoked"):
            return {
                "valid": False,
                "status": "REVOKED",
                "message": "Ruhsat iptal edilmiş",
                "revoked_at": license_data.get("revoked_at"),
                "reason": license_data.get("revoke_reason")
            }
        
        # Check expired
        expiry_date = datetime.fromisoformat(license_data["expiry_date"])
        if datetime.now() > expiry_date:
            return {
                "valid": False,
                "status": "EXPIRED",
                "message": "Ruhsatın süresi dolmuş",
                "expiry_date": license_data["expiry_date"]
            }
        
        # Valid
        return {
            "valid": True,
            "status": "ACTIVE",
            "message": "Ruhsat geçerli",
            "data": license_data
        }
    
    def _is_authorized_issuer(self, issuer_did: str) -> bool:
        """Check if issuer is in authorized list"""
        # In production: load from config or database
        authorized_issuers = [
            config.ISSUER_DID,
            "did:indy:konya:BelediyeBaskanligi"
        ]
        return issuer_did in authorized_issuers
    
    def _license_exists(self, license_id: str) -> bool:
        """Check if license exists in contract state"""
        return license_id in self.state
    
    def get_license_count(self) -> dict:
        """Get statistics"""
        active = sum(1 for lic in self.state.values() if lic.get("status") == "ACTIVE")
        revoked = sum(1 for lic in self.state.values() if lic.get("revoked"))
        
        return {
            "total": len(self.state),
            "active": active,
            "revoked": revoked
        }
    
    def get_all_licenses(self) -> list:
        """Get all licenses (for admin)"""
        return list(self.state.values())


# Test
if __name__ == "__main__":
    contract = LicenseSmartContract()
    
    print("\n=== SMART CONTRACT TEST ===\n")
    
    # Test 1: Valid license
    result = contract.issue_license({
        "license_id": "2024-KON-TEST-001",
        "license_type": "Restaurant License",
        "owner_name": "Test User",
        "citizen_id": "12345678901",
        "region": "Selçuklu",
        "issue_date": "2024-01-01",
        "expiry_date": "2025-01-01"
    }, issuer_did=config.ISSUER_DID)
    
    print("Test 1 - Valid License:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test 2: Duplicate license (should fail)
    result2 = contract.issue_license({
        "license_id": "2024-KON-TEST-001",
        "license_type": "Cafe License",
        "owner_name": "Another User",
        "citizen_id": "98765432109",
        "region": "Meram",
        "issue_date": "2024-01-01",
        "expiry_date": "2025-01-01"
    }, issuer_did=config.ISSUER_DID)
    
    print("\nTest 2 - Duplicate (should fail):")
    print(json.dumps(result2, indent=2, ensure_ascii=False))
    
    # Test 3: Invalid dates (should fail)
    result3 = contract.issue_license({
        "license_id": "2024-KON-TEST-002",
        "license_type": "Restaurant",
        "owner_name": "Test",
        "citizen_id": "11111111111",
        "region": "Selçuklu",
        "issue_date": "2025-01-01",
        "expiry_date": "2024-01-01"  # Before issue date!
    }, issuer_did=config.ISSUER_DID)
    
    print("\nTest 3 - Invalid Dates (should fail):")
    print(json.dumps(result3, indent=2, ensure_ascii=False))
    
    # Test 4: Verify
    verify = contract.verify_license("2024-KON-TEST-001")
    print("\nTest 4 - Verify:")
    print(json.dumps(verify, indent=2, ensure_ascii=False))
    
    # Test 5: Revoke
    revoke = contract.revoke_license(
        "2024-KON-TEST-001",
        config.ISSUER_DID,
        "Test amaçlı iptal"
    )
    print("\nTest 5 - Revoke:")
    print(json.dumps(revoke, indent=2, ensure_ascii=False))
    
    # Stats
    stats = contract.get_license_count()
    print("\nStatistics:")
    print(json.dumps(stats, indent=2))