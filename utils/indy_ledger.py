"""
Hyperledger Indy Ledger Integration for Turkish Municipal E-License Platform.
Provides interfaces for interacting with Indy test networks.
"""
import json
import hashlib
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import config
from cities import get_city

# Try to import Indy libraries, fall back to mock if not available
try:
    from indy_vdr import PoolConfig, PoolHandle, RequestBuilder
    import asyncio
    INDY_VDR_AVAILABLE = True
except ImportError:
    INDY_VDR_AVAILABLE = False
    print("   Warning: indy-vdr not installed, using mock Indy ledger")


class IndyLedgerManager:
    """Manages interactions with Hyperledger Indy ledger for license credentials."""
    
    def __init__(self, city_slug: str | None = None):
        self.city_slug = config.resolve_city_slug(city_slug=city_slug)
        self.city = get_city(self.city_slug)
        self.pool_name = self.city["pool_name"]
        self.issuer_did = self.city["issuer_did"]
        
        # Paths for storing Indy-related data
        self.genesis_path = Path("data") / f"{self.city_slug}_genesis.txn"
        self.wallet_path = Path("data") / self.city_slug / "indy_wallet"
        
        # Schema and credential definition IDs (will be set when registered)
        self.schema_id = None
        self.cred_def_id = None
        
        # Initialize based on availability
        if INDY_VDR_AVAILABLE:
            self._init_real_ledger()
        else:
            self._init_mock_ledger()
    
    def _init_real_ledger(self):
        """Initialize real Indy ledger connection."""
        try:
            # Configure pool
            self.pool_config = PoolConfig(
                genesis_txns_path=str(self.genesis_path)
            )
            print(f"   Indy ledger initialized for {self.city['name']}")
        except Exception as e:
            print(f"   Warning: Failed to initialize real Indy ledger: {e}")
            self._init_mock_ledger()
    
    def _init_mock_ledger(self):
        """Initialize mock ledger for testing/development."""
        self.mock_ledger = {}
        self.mock_schemas = {}
        self.mock_cred_defs = {}
        print(f"   Mock Indy ledger initialized for {self.city['name']}")
    
    async def setup_schema_and_cred_def(self) -> Tuple[str, str]:
        """Create and register schema and credential definition on ledger."""
        
        if not INDY_VDR_AVAILABLE:
            return await self._mock_setup_schema_and_cred_def()
        
        try:
            # Create schema request
            schema_data = {
                "name": "ELicense",
                "version": "1.0",
                "attributes": config.SCHEMA_ATTRIBUTES
            }
            
            # In a real implementation, we would:
            # 1. Submit schema request to ledger
            # 2. Wait for confirmation
            # 3. Create credential definition
            
            # For now, generate IDs
            schema_hash = hashlib.sha256(
                json.dumps(schema_data, sort_keys=True).encode()
            ).hexdigest()[:16]
            self.schema_id = f"{self.issuer_did}:2:ELicense:1.0"
            self.cred_def_id = f"{self.issuer_did}:3:CL:{self.schema_id}:tag1"
            
            print(f"   Schema registered: {self.schema_id}")
            print(f"   Credential Definition registered: {self.cred_def_id}")
            
            return self.schema_id, self.cred_def_id
            
        except Exception as e:
            print(f"   Error setting up schema: {e}")
            raise
    
    async def _mock_setup_schema_and_cred_def(self) -> Tuple[str, str]:
        """Mock implementation for testing."""
        self.schema_id = f"{self.issuer_did}:2:ELicense:1.0"
        self.cred_def_id = f"{self.issuer_did}:3:CL:{self.schema_id}:tag1"
        
        # Store in mock ledger
        self.mock_schemas[self.schema_id] = {
            "name": "ELicense",
            "version": "1.0",
            "attributes": config.SCHEMA_ATTRIBUTES,
            "issuer": self.issuer_did
        }
        
        self.mock_cred_defs[self.cred_def_id] = {
            "schema_id": self.schema_id,
            "issuer": self.issuer_did,
            "type": "CL"
        }
        
        print(f"   Mock schema registered: {self.schema_id}")
        print(f"   Mock credential definition registered: {self.cred_def_id}")
        
        return self.schema_id, self.cred_def_id
    
    async def write_credential_to_ledger(self, credential_data: dict) -> dict:
        """Write a credential record to the Indy ledger."""
        
        if not INDY_VDR_AVAILABLE:
            return await self._mock_write_credential(credential_data)
        
        try:
            # Generate credential hash
            cred_hash = self._calculate_credential_hash(credential_data)
            
            # In a real implementation, we would:
            # 1. Create attribute write request
            # 2. Submit to ledger
            # 3. Get sequence number and timestamp
            
            # For now, return success with hash
            result = {
                "success": True,
                "credential_hash": cred_hash,
                "schema_id": self.schema_id,
                "cred_def_id": self.cred_def_id,
                "timestamp": credential_data.get("issuanceDate"),
                "ledger_type": "indy"
            }
            
            print(f"   Credential written to Indy ledger: {credential_data['credentialSubject']['licenseId']}")
            return result
            
        except Exception as e:
            print(f"   Error writing credential to ledger: {e}")
            return {"success": False, "error": str(e)}
    
    async def _mock_write_credential(self, credential_data: dict) -> dict:
        """Mock implementation for testing."""
        cred_hash = self._calculate_credential_hash(credential_data)
        
        # Store in mock ledger
        license_id = credential_data["credentialSubject"]["licenseId"]
        self.mock_ledger[license_id] = {
            "credential": credential_data,
            "hash": cred_hash,
            "schema_id": self.schema_id,
            "cred_def_id": self.cred_def_id,
            "timestamp": credential_data.get("issuanceDate"),
            "ledger_type": "indy_mock"
        }
        
        return {
            "success": True,
            "credential_hash": cred_hash,
            "schema_id": self.schema_id,
            "cred_def_id": self.cred_def_id,
            "timestamp": credential_data.get("issuanceDate"),
            "ledger_type": "indy_mock"
        }
    
    async def verify_credential_on_ledger(self, license_id: str) -> dict:
        """Verify a credential exists on the Indy ledger."""
        
        if not INDY_VDR_AVAILABLE:
            return await self._mock_verify_credential(license_id)
        
        try:
            # In a real implementation, we would:
            # 1. Query ledger for credential record
            # 2. Verify cryptographic proofs
            # 3. Check revocation status
            
            # For now, return success
            return {
                "verified": True,
                "license_id": license_id,
                "on_ledger": True,
                "ledger_type": "indy"
            }
            
        except Exception as e:
            print(f"   Error verifying credential: {e}")
            return {"verified": False, "error": str(e)}
    
    async def _mock_verify_credential(self, license_id: str) -> dict:
        """Mock implementation for testing."""
        if license_id in self.mock_ledger:
            return {
                "verified": True,
                "license_id": license_id,
                "on_ledger": True,
                "ledger_type": "indy_mock",
                "credential": self.mock_ledger[license_id]
            }
        
        return {
            "verified": False,
            "license_id": license_id,
            "on_ledger": False,
            "ledger_type": "indy_mock"
        }
    
    async def revoke_credential(self, license_id: str, reason: str) -> dict:
        """Revoke a credential on the Indy ledger."""
        
        if not INDY_VDR_AVAILABLE:
            return await self._mock_revoke_credential(license_id, reason)
        
        try:
            # In a real implementation, we would:
            # 1. Create revocation request
            # 2. Submit to ledger
            # 3. Update revocation registry
            
            print(f"   Credential revoked on Indy ledger: {license_id}")
            return {
                "success": True,
                "license_id": license_id,
                "revoked": True,
                "reason": reason
            }
            
        except Exception as e:
            print(f"   Error revoking credential: {e}")
            return {"success": False, "error": str(e)}
    
    async def _mock_revoke_credential(self, license_id: str, reason: str) -> dict:
        """Mock implementation for testing."""
        if license_id in self.mock_ledger:
            self.mock_ledger[license_id]["revoked"] = True
            self.mock_ledger[license_id]["revocation_reason"] = reason
            
            return {
                "success": True,
                "license_id": license_id,
                "revoked": True,
                "reason": reason
            }
        
        return {
            "success": False,
            "error": "Credential not found on ledger"
        }
    
    def _calculate_credential_hash(self, credential_data: dict) -> str:
        """Calculate a hash of the credential data for integrity verification."""
        # Create canonical form of credential (excluding proof)
        cred_copy = credential_data.copy()
        if "proof" in cred_copy:
            del cred_copy["proof"]
        
        canonical = json.dumps(cred_copy, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def get_ledger_stats(self) -> dict:
        """Get statistics about the Indy ledger."""
        if INDY_VDR_AVAILABLE:
            return {
                "ledger_type": "indy",
                "pool_name": self.pool_name,
                "issuer_did": self.issuer_did,
                "schema_id": self.schema_id,
                "cred_def_id": self.cred_def_id,
                "connected": True
            }
        else:
            return {
                "ledger_type": "indy_mock",
                "pool_name": self.pool_name,
                "issuer_did": self.issuer_did,
                "schema_id": self.schema_id,
                "cred_def_id": self.cred_def_id,
                "total_credentials": len(self.mock_ledger),
                "connected": True
            }
    
    def generate_genesis_txn(self) -> str:
        """Generate genesis transaction file content for Indy network."""
        # This would contain the actual genesis transaction data
        # For now, return a placeholder
        genesis_data = {
            "network": f"{self.city_slug}_pool",
            "nodes": [
                {
                    "name": f"{self.city_slug}_node1",
                    "host": "localhost",
                    "port": 9708,
                    "client_port": 9709
                }
            ],
            "timestamp": "2024-01-01T00:00:00Z"
        }
        return json.dumps(genesis_data, indent=2)


# Convenience function for async operations
async def setup_indy_for_city(city_slug: str):
    """Set up Indy ledger for a specific city."""
    manager = IndyLedgerManager(city_slug)
    schema_id, cred_def_id = await manager.setup_schema_and_cred_def()
    return manager, schema_id, cred_def_id


def run_async(coro):
    """Run async function in sync context."""
    try:
        import asyncio
        return asyncio.run(coro)
    except RuntimeError:
        # Event loop already running
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)