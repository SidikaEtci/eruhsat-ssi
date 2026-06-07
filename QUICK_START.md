# Quick Start Guide - Hyperledger Indy Integration

## 3-Minute Setup

### Option 1: Mock Indy (No Setup Required!)

Just run the application - it will automatically use a mock Indy ledger:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API
python api.py

# Open browser
# http://localhost:8000
```

That's it! The mock ledger works exactly like real Indy for testing.

### Option 2: Real Indy with Von Network (5 minutes)

#### Step 1: Start Von Network
```bash
docker run -d \
  --name von-network \
  -p 9000:8000 \
  -p 9708:9708 \
  -p 9709:9709 \
  ghcr.io/hyperledger/indy-plenum:latest

# Wait 30 seconds
sleep 30
```

#### Step 2: Get Genesis Transaction
```bash
curl http://localhost:9000/genesis > data/genesis.txn
```

#### Step 3: Start the API
```bash
python api.py
```

## Testing (1 minute)

### Automated Test
```bash
python test_indy.py
```

### Manual Test
1. Open browser: http://localhost:8000
2. Issue a test license
3. Check console for: `✓ Credential written to Hyperledger Indy`
4. Visit: http://localhost:8000/api/indy/stats

## That's It!

You now have a working Hyperledger Indy integration.

## Common Commands

```bash
# Start everything
python api.py

# Run tests
python test_indy.py

# Stop Von Network
docker rm -f von-network

# View logs
docker logs von-network
```

## Need Help?

- Full documentation: `INDY_SETUP.md`
- Von Network guide: `VON_NETWORK_SETUP.md`
- API docs: http://localhost:8000/docs