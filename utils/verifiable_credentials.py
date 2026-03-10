"""
W3C Verifiable Credentials Implementation
Using Hyperledger Indy for DID and Credential Management
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from datetime import datetime, timedelta
import hashlib
import base64
from typing import Dict, List, Optional
from utils.crypto import CryptoManager
import config


class VerifiableCredentialManager:
    """
    Manages W3C Verifiable Credentials
    
    VC Structure:
    {
        "@context": [...],
        "type": ["VerifiableCredential", "LicenseCredential"],
        "issuer": "did:indy:konya:KBB",
        "issuanceDate": "2024-01-01T00:00:00Z",
        "credentialSubject": {
            "id": "did:indy:konya:holder123",
            "licenseType": "Restaurant License",
            "region": "Selçuklu",
            "validUntil": "2025-01-01"
        },
        "proof": {...}
    }
    """
    
    def __init__(self):
        self.private_key, self.public_key = CryptoManager.generate_keypair(
            seed=config.ISSUER_SEED
        )
        self.issuer_did = config.ISSUER_DID
    
    def create_credential(self, license_data: dict) -> dict:
        """
        Create W3C Verifiable Credential
        
        IMPORTANT: Only includes non-sensitive data
        """
        
        # Create holder DID (normally holder generates this)
        holder_did = self._create_holder_did(license_data['citizen_id'])
        
        # Credential Subject - PUBLIC DATA ONLY
        credential_subject = {
            "id": holder_did,
            "licenseId": license_data['license_id'],
            "licenseType": license_data['license_type'],
            "region": license_data['region'],
            "validFrom": license_data['issue_date'],
            "validUntil": license_data['expiry_date'],
            # NO: citizen_id, owner_name, address, phone
        }
        
        # Create Verifiable Credential
        credential = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://konya.gov.tr/credentials/v1"
            ],
            "type": ["VerifiableCredential", "LicenseCredential"],
            "issuer": {
                "id": self.issuer_did,
                "name": config.ISSUER_NAME
            },
            "issuanceDate": datetime.now().isoformat() + "Z",
            "expirationDate": (datetime.now() + timedelta(days=365)).isoformat() + "Z",
            "credentialSubject": credential_subject
        }
        
        # Add cryptographic proof
        credential["proof"] = self._create_proof(credential)
        
        return credential
    
    def _create_holder_did(self, citizen_id: str) -> str:
        """
        Create DID for holder (license owner)
        
        In production, holder should generate this themselves
        """
        # Hash citizen_id to create pseudonymous DID
        hashed = hashlib.sha256(citizen_id.encode()).hexdigest()[:16]
        return f"did:indy:konya:{hashed}"
    
    def _create_proof(self, credential: dict) -> dict:
        """
        Create cryptographic proof for credential
        
        Uses Ed25519 signature (same as Indy)
        """
        # Canonical JSON (sorted keys)
        canonical = json.dumps(credential, sort_keys=True, ensure_ascii=False)
        
        # Sign
        signature = CryptoManager.sign_data(canonical, self.private_key)
        
        return {
            "type": "Ed25519Signature2020",
            "created": datetime.now().isoformat() + "Z",
            "verificationMethod": f"{self.issuer_did}#keys-1",
            "proofPurpose": "assertionMethod",
            "proofValue": signature
        }
    
    def verify_credential(self, credential: dict) -> tuple[bool, str]:
        """
        Verify Verifiable Credential
        
        Returns: (is_valid, message)
        """
        try:
            # Extract proof
            proof = credential.get("proof")
            if not proof:
                return False, "No proof found"
            
            # Remove proof for verification
            credential_copy = credential.copy()
            del credential_copy["proof"]
            
            # Canonical JSON
            canonical = json.dumps(credential_copy, sort_keys=True, ensure_ascii=False)
            
            # Verify signature
            is_valid = CryptoManager.verify_signature(
                canonical,
                proof["proofValue"],
                self.public_key
            )
            
            if not is_valid:
                return False, "Invalid signature"
            
            # Check expiration
            expiration = credential.get("expirationDate")
            if expiration:
                exp_date = datetime.fromisoformat(expiration.replace("Z", ""))
                if datetime.now() > exp_date:
                    return False, "Credential expired"
            
            return True, "Credential valid"
        
        except Exception as e:
            return False, f"Verification error: {str(e)}"
    
    def create_presentation(self, credential: dict, disclosed_attributes: List[str]) -> dict:
        """
        Create Verifiable Presentation (selective disclosure)
        
        This is where ZKP would be used in production
        
        Example:
            disclosed_attributes = ["licenseType", "region"]
            # Does NOT disclose: licenseId, dates, etc.
        """
        
        # Filter credential subject
        full_subject = credential["credentialSubject"]
        disclosed_subject = {
            k: v for k, v in full_subject.items() 
            if k in disclosed_attributes or k == "id"
        }
        
        # Create presentation
        presentation = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1"
            ],
            "type": ["VerifiablePresentation"],
            "verifiableCredential": [{
                **credential,
                "credentialSubject": disclosed_subject
            }],
            "holder": full_subject["id"]
        }
        
        # Add presentation proof
        presentation["proof"] = self._create_presentation_proof(presentation)
        
        return presentation
    
    def _create_presentation_proof(self, presentation: dict) -> dict:
        """Create proof for presentation (normally holder signs this)"""
        canonical = json.dumps(presentation, sort_keys=True, ensure_ascii=False)
        signature = CryptoManager.sign_data(canonical, self.private_key)
        
        return {
            "type": "Ed25519Signature2020",
            "created": datetime.now().isoformat() + "Z",
            "verificationMethod": f"{self.issuer_did}#keys-1",
            "proofPurpose": "authentication",
            "challenge": hashlib.sha256(str(datetime.now()).encode()).hexdigest(),
            "proofValue": signature
        }
    
    def create_zkp_proof(self, credential: dict, claim: str) -> dict:
        """
        Create Zero-Knowledge Proof
        
        Example claims:
        - "age >= 18" (without revealing exact age)
        - "license is valid" (without revealing dates)
        - "region is Selçuklu" (without revealing exact address)
        
        This is a simplified version. Full ZKP requires:
        - Hyperledger Indy's AnonCreds
        - Cryptographic accumulators
        - Range proofs
        """
        
        subject = credential["credentialSubject"]
        
        # Parse claim
        if "valid" in claim.lower():
            # Prove license is currently valid
            valid_until = datetime.fromisoformat(subject["validUntil"])
            is_valid = datetime.now() < valid_until
            
            return {
                "type": "ZeroKnowledgeProof",
                "claim": "License is currently valid",
                "proof": {
                    "result": is_valid,
                    "timestamp": datetime.now().isoformat(),
                    # In real ZKP: cryptographic proof without revealing dates
                    "note": "Real ZKP would not reveal validUntil date"
                }
            }
        
        elif "region" in claim.lower():
            # Prove region membership without revealing exact location
            region = subject["region"]
            
            return {
                "type": "ZeroKnowledgeProof",
                "claim": f"License is valid in specified region",
                "proof": {
                    "result": True,
                    "region_hash": hashlib.sha256(region.encode()).hexdigest(),
                    # Verifier can check hash without knowing region
                }
            }
        
        return {
            "type": "ZeroKnowledgeProof",
            "claim": claim,
            "proof": {"error": "Unsupported claim"}
        }


# Example usage
if __name__ == "__main__":
    vc_manager = VerifiableCredentialManager()
    
    # Create credential
    license_data = {
        "license_id": "2024-KON-001",
        "license_type": "Restaurant License",
        "citizen_id": "12345678901",
        "owner_name": "Ahmet Yılmaz",
        "region": "Selçuklu",
        "issue_date": "2024-01-01",
        "expiry_date": "2025-01-01"
    }
    
    credential = vc_manager.create_credential(license_data)
    print("\n📜 Verifiable Credential:")
    print(json.dumps(credential, indent=2, ensure_ascii=False))
    
    # Verify
    is_valid, message = vc_manager.verify_credential(credential)
    print(f"\n✅ Verification: {is_valid} - {message}")
    
    # Selective disclosure
    presentation = vc_manager.create_presentation(
        credential,
        disclosed_attributes=["licenseType", "region"]
    )
    print("\n🎭 Verifiable Presentation (Selective Disclosure):")
    print(json.dumps(presentation, indent=2, ensure_ascii=False))
    
    # ZKP
    zkp = vc_manager.create_zkp_proof(credential, "license is valid")
    print("\n🔐 Zero-Knowledge Proof:")
    print(json.dumps(zkp, indent=2, ensure_ascii=False))
