# Von Network Quick Setup Guide

This guide shows you how to set up a real Hyperledger Indy network using Von Network for testing.

## What is Von Network?

Von Network is a Docker-based Hyperledger Indy network perfect for testing and development. It's like a local Indy blockchain you can run on your computer.

## Prerequisites

- Docker installed
- Docker Compose installed
- Python 3.11+

## Step-by-Step Setup

### 1. Start Von Network

Open a terminal and run:

```bash
# Start Von Network (Indy blockchain)
docker run -d \
  --name von-network \
  -p 9000:8000 \
  -p 9708:9708 \
  -p 9709:9709 \
  ghcr.io/hyperledger/indy-plenum:latest
```

Wait 30 seconds for it to start, then check if it's running:

```bash
docker ps | grep von-network
```

You should see the container running.

### 2. Get Genesis Transaction

Open your browser and go to:
```
http://localhost:9000/genesis
```

You'll see the genesis transaction text. Copy all of it.

Create a file called `data/genesis.txn` and paste the content:

```bash
# Create the file
mkdir -p data
nano data/genesis.txn

# Paste the genesis content and save (Ctrl+X, Y, Enter)
```

Or use this command to download automatically:

```bash
curl http://localhost:9000/genesis > data/genesis.txn
```

### 3. Update Configuration

Edit `indy_config.json`:

```json
{
  "indy": {
    "enabled": true,
    "network": "test",
    "pool_name": "von-network",
    "genesis_txn_path": "data/genesis.txn",
    "wallet_storage_path": "data/{city_slug}/indy_wallet"
  }
}
```

### 4. Install Indy Libraries (Optional)

For real Indy integration, install the libraries:

```bash
pip install indy-vdr==0.3.3 indy-credx==1.0.0 aries-askar==0.3.0
```

**Note**: If you skip this step, the system will use a mock ledger (still works for testing!).

### 5. Start the Application

```bash
python api.py
```

## Testing the Integration

### Test 1: Check Indy Stats

Open your browser and go to:
```
http://localhost:8000/api/indy/stats
```

You should see something like:
```json
{
  "success": true,
  "city_slug": "konya",
  "stats": {
    "ledger_type": "indy",
    "pool_name": "konya_pool",
    "issuer_did": "did:indy:tr:konya:municipality",
    "schema_id": "did:indy:tr:konya:municipality:2:ELicense:1.0",
    "cred_def_id": "did:indy:tr:konya:municipality:3:CL:did:indy:tr:konya:municipality:2:ELicense:1.0:tag1",
    "connected": true
  }
}
```

### Test 2: Issue a License

Use the web interface or API to issue a license. Watch the console output for:
```
✓ Credential written to Hyperledger Indy
```

### Test 3: Verify on Indy

After issuing a license (e.g., `2024-KON-001`), verify it on Indy:

```
http://localhost:8000/api/indy/verify/2024-KON-001
```

You should see:
```json
{
  "verified": true,
  "license_id": "2024-KON-001",
  "on_ledger": true,
  "ledger_type": "indy"
}
```

## Easy Testing Script

Create a file called `test_indy.py`:

```python
#!/usr/bin/env python3
"""Simple test script for Indy integration."""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_indy_stats():
    """Test Indy stats endpoint."""
    print("Testing Indy stats...")
    response = requests.get(f"{BASE_URL}/api/indy/stats")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Indy stats: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"✗ Failed: {response.status_code}")
        return False

def test_issue_license():
    """Test issuing a license."""
    print("\nTesting license issuance...")
    
    license_data = {
        "license_id": "2024-TEST-001",
        "license_type": "Test License",
        "owner_name": "Test User",
        "business_name": "Test Business",
        "address": "Test Address",
        "citizen_id": "12345678901",
        "region": "Selçuklu",
        "issue_date": "2024-01-01",
        "expiry_date": "2025-01-01",
        "city_slug": "konya"
    }
    
    response = requests.post(f"{BASE_URL}/api/issue", data=license_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ License issued: {result['data']['license_id']}")
        if result['data'].get('indy_hash'):
            print(f"  Indy hash: {result['data']['indy_hash']}")
        return True
    else:
        print(f"✗ Failed: {response.status_code}")
        return False

def test_verify_on_indy(license_id="2024-TEST-001"):
    """Test verifying a license on Indy."""
    print(f"\nTesting Indy verification for {license_id}...")
    
    response = requests.get(f"{BASE_URL}/api/indy/verify/{license_id}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get('verified'):
            print(f"✓ License verified on Indy!")
            print(f"  On ledger: {result['on_ledger']}")
            return True
        else:
            print(f"✗ License not verified")
            return False
    else:
        print(f"✗ Failed: {response.status_code}")
        return False

def main():
    print("=" * 60)
    print("Hyperledger Indy Integration Test")
    print("=" * 60)
    
    tests = [
        test_indy_stats,
        test_issue_license,
        test_verify_on_indy
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("✓ All tests passed! Indy integration is working.")
    else:
        print("✗ Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()
```

Run the test:

```bash
python test_indy.py
```

## Using Docker Compose (Easiest Method)

The easiest way is to use the provided Docker Compose file:

```bash
# Start everything (Von Network + API + IPFS)
docker-compose -f docker-compose.indy.yml up
```

This starts:
- Von Network (Indy blockchain)
- E-License API
- IPFS (for document storage)

Everything is pre-configured and ready to use!

## Troubleshooting

### Von Network Won't Start

**Problem**: Docker container exits immediately

**Solution**: 
```bash
# Remove old container
docker rm -f von-network

# Try again
docker run -d \
  --name von-network \
  -p 9000:8000 \
  -p 9708:9708 \
  -p 9709:9709 \
  ghcr.io/hyperledger/indy-plenum:latest
```

### Cannot Connect to Von Network

**Problem**: Connection refused

**Solution**: Wait 30 seconds after starting Von Network, then try again.

### Indy Libraries Won't Install

**Problem**: `pip install indy-vdr` fails

**Solution**: Use mock ledger (no action needed - it's automatic!)

### Port Already in Use

**Problem**: Port 9000 or 8000 already in use

**Solution**: Use different ports:
```bash
# For Von Network
docker run -d \
  --name von-network \
  -p 9001:8000 \
  -p 9710:9708 \
  -p 9711:9709 \
  ghcr.io/hyperledger/indy-plenum:latest

# Then update indy_config.json with new ports
```

## Quick Reference

### Start Everything
```bash
# Terminal 1: Start Von Network
docker run -d --name von-network -p 9000:8000 -p 9708:9708 -p 9709:9709 ghcr.io/hyperledger/indy-plenum:latest

# Wait 30 seconds, then Terminal 2: Start API
python api.py
```

### Test
```bash
# Run automated tests
python test_indy.py

# Or test manually in browser:
# http://localhost:8000/api/indy/stats
# http://localhost:8000/api/indy/verify/2024-KON-001
```

### Stop Everything
```bash
docker rm -f von-network
```

## Next Steps

Once you have Von Network working:

1. **Issue real licenses** through the web interface
2. **Verify them on Indy** using the API
3. **Check the blockchain explorer** at http://localhost:8000/blockchain_explorer.html
4. **Try revocation** using the Indy revoke endpoint

That's it! You now have a real Hyperledger Indy network for testing.