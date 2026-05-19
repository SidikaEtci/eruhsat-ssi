"""
Simple blockchain-style ledger for demonstration
"""
import json
from datetime import datetime
from pathlib import Path
import hashlib
import config


class BlockchainLogger:
    """Simple blockchain ledger (per municipality)."""

    def __init__(self, city_slug: str | None = None):
        self.city_slug = config.resolve_city_slug(city_slug=city_slug)
        self.city = __import__("cities").get_city(self.city_slug)
        self.ledger_file = config.paths_for_city(self.city_slug)["data_dir"] / "blockchain_ledger.json"

        if not self.ledger_file.exists():
            self._create_genesis_block()
            print(f"   Genesis block created for {self.city['name']}")

    def _create_genesis_block(self):
        """Create first block"""
        genesis = {
            "block_number": 0,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "type": "GENESIS",
                "city_slug": self.city_slug,
                "city_name": self.city["name"],
                "message": f"{self.city['name']} E-License Blockchain Started",
            },
            "previous_hash": "0" * 64,
            "hash": None
        }
        
        # Calculate hash
        genesis["hash"] = self._calculate_hash(genesis)
        
        # Save
        with open(self.ledger_file, 'w', encoding='utf-8') as f:
            json.dump([genesis], f, indent=2, ensure_ascii=False)
    
    def _calculate_hash(self, block):
        """Calculate block hash"""
        # Create hash input (exclude hash field itself)
        hash_input = {
            "block_number": block["block_number"],
            "timestamp": block["timestamp"],
            "data": block["data"],
            "previous_hash": block["previous_hash"]
        }
        
        block_string = json.dumps(hash_input, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def add_block(self, data: dict):
        """Add new block to ledger"""
        try:
            # Load existing ledger
            with open(self.ledger_file, 'r', encoding='utf-8') as f:
                ledger = json.load(f)
            
            # Get previous block
            previous_block = ledger[-1]
            
            # Create new block
            new_block = {
                "block_number": len(ledger),
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "previous_hash": previous_block["hash"],
                "hash": None
            }
            
            # Calculate hash
            new_block["hash"] = self._calculate_hash(new_block)
            
            # Add to ledger
            ledger.append(new_block)
            
            # Save
            with open(self.ledger_file, 'w', encoding='utf-8') as f:
                json.dump(ledger, f, indent=2, ensure_ascii=False)
            
            print(f"   Block #{new_block['block_number']} added to blockchain")
            print(f"   Hash: {new_block['hash'][:32]}...")
            
            return new_block
        
        except Exception as e:
            print(f"   Error adding block: {e}")
            return None
    
    def get_ledger(self):
        """Get entire ledger"""
        try:
            with open(self.ledger_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def verify_chain(self):
        """Verify blockchain integrity"""
        try:
            ledger = self.get_ledger()
            
            if len(ledger) == 0:
                return False, "Empty ledger"
            
            # Check each block
            for i in range(1, len(ledger)):
                current = ledger[i]
                previous = ledger[i-1]
                
                # Recalculate hash
                calculated_hash = self._calculate_hash(current)
                
                # Verify hash
                if current["hash"] != calculated_hash:
                    return False, f"Block {i} hash invalid"
                
                # Verify chain
                if current["previous_hash"] != previous["hash"]:
                    return False, f"Block {i} chain broken"
            
            return True, "Blockchain is valid"
        
        except Exception as e:
            return False, f"Verification error: {e}"
    
    def get_stats(self):
        """Get blockchain statistics"""
        ledger = self.get_ledger()
        valid, message = self.verify_chain()
        
        return {
            "total_blocks": len(ledger),
            "is_valid": valid,
            "validation_message": message,
            "genesis_time": ledger[0]["timestamp"] if ledger else None,
            "latest_time": ledger[-1]["timestamp"] if ledger else None
        }
