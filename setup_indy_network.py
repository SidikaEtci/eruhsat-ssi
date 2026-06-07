#!/usr/bin/env python3
"""
Setup script for Hyperledger Indy test network integration.
This script helps configure and initialize Indy network for the e-license platform.
"""
import os
import sys
import json
from pathlib import Path

def check_indy_vdr():
    """Check if indy-vdr is installed."""
    try:
        import indy_vdr
        print("✓ indy-vdr is installed")
        return True
    except ImportError:
        print("✗ indy-vdr is not installed")
        return False

def install_dependencies():
    """Install required dependencies."""
    print("\n=== Installing Dependencies ===")
    
    if check_indy_vdr():
        print("indy-vdr is already installed")
    else:
        print("Installing indy-vdr...")
        os.system("pip install indy-vdr==0.3.3")
    
    # Check other required packages
    required_packages = ["indy-credx", "aries-askar"]
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is not installed")
            print(f"  Install with: pip install {package}")

def generate_genesis_transaction():
    """Generate genesis transaction for Indy network."""
    print("\n=== Generating Genesis Transaction ===")
    
    # Import cities to get all city configurations
    try:
        from cities import CITIES, DEFAULT_CITY_SLUG
    except ImportError:
        print("Error: Could not import cities module")
        return False
    
    genesis_data = {
        "network": "turkey_elicense_testnet",
        "version": "1.0",
        "nodes": [],
        "metadata": {
            "description": "Turkey Municipal E-License Hyperledger Indy Test Network",
            "created": "2024-01-01T00:00:00Z",
            "supported_cities": list(CITIES.keys()),
            "default_city": DEFAULT_CITY_SLUG
        }
    }
    
    # Generate node configurations for each city
    base_port = 9708
    for idx, (city_slug, city_data) in enumerate(CITIES.items()):
        node_config = {
            "name": f"{city_slug}_node",
            "host": "localhost",
            "port": base_port + (idx * 10),
            "client_port": base_port + (idx * 10) + 1,
            "pool_name": city_data["pool_name"],
            "issuer_did": city_data["issuer_did"]
        }
        genesis_data["nodes"].append(node_config)
    
    # Save genesis transaction
    genesis_path = Path("data/genesis_txn.json")
    with open(genesis_path, 'w', encoding='utf-8') as f:
        json.dump(genesis_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Genesis transaction saved to {genesis_path}")
    print(f"  Total nodes configured: {len(genesis_data['nodes'])}")
    
    return True

def setup_wallet_storage():
    """Set up secure wallet storage for Indy credentials."""
    print("\n=== Setting Up Wallet Storage ===")
    
    try:
        from cities import CITIES
    except ImportError:
        print("Error: Could not import cities module")
        return False
    
    # Create wallet directories for each city
    data_dir = Path("data")
    for city_slug in CITIES.keys():
        wallet_dir = data_dir / city_slug / "indy_wallet"
        wallet_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Wallet directory created: {wallet_dir}")
    
    return True

def create_indy_config():
    """Create Indy configuration file."""
    print("\n=== Creating Indy Configuration ===")
    
    config_data = {
        "indy": {
            "enabled": True,
            "network": "test",
            "pool_name": "turkey_elicense_pool",
            "genesis_txn_path": "data/genesis_txn.json",
            "wallet_storage_path": "data/{city_slug}/indy_wallet",
            "auto_setup": True
        },
        "schema": {
            "name": "ELicense",
            "version": "1.0",
            "attributes": [
                "license_id",
                "license_type",
                "city",
                "issue_date",
                "expiry_date",
                "district",
                "ipfs_hash",
                "document_hash"
            ]
        },
        "credential_definition": {
            "tag": "tag1",
            "signature_type": "CL"
        }
    }
    
    config_path = Path("indy_config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Indy configuration saved to {config_path}")
    return True

def display_setup_instructions():
    """Display next steps for the user."""
    print("\n=== Setup Complete! Next Steps ===")
    print("""
1. If you want to use a real Hyperledger Indy network:
   - Set up an Indy network (von-network for testing)
   - Update indy_config.json with network details
   - Run: python -m indy_cli start

2. For development/testing with mock Indy ledger:
   - The system will automatically use mock ledger if indy-vdr is not available
   - No additional setup required

3. To start the application:
   - API: python api.py
   - CLI: python main.py

4. The system will automatically:
   - Register schemas and credential definitions on first use
   - Write credentials to Indy ledger (or mock ledger)
   - Maintain backward compatibility with local blockchain

5. Verify Indy integration:
   - Issue a license through the API or CLI
   - Check console output for "✓ Credential written to Hyperledger Indy"
   - View blockchain explorer at: http://localhost:8000/blockchain_explorer.html
    """)

def main():
    """Main setup function."""
    print("=" * 60)
    print("  Hyperledger Indy Network Setup for Turkey E-License Platform")
    print("=" * 60)
    
    # Step 1: Install dependencies
    install_dependencies()
    
    # Step 2: Generate genesis transaction
    if not generate_genesis_transaction():
        print("Warning: Failed to generate genesis transaction")
    
    # Step 3: Setup wallet storage
    if not setup_wallet_storage():
        print("Warning: Failed to setup wallet storage")
    
    # Step 4: Create configuration
    if not create_indy_config():
        print("Warning: Failed to create Indy configuration")
    
    # Step 5: Display instructions
    display_setup_instructions()
    
    print("\n✓ Indy integration setup completed successfully!")
    print("  You can now use the e-license platform with Hyperledger Indy support.")

if __name__ == "__main__":
    main()