# Hyperledger Indy Integration Guide

This guide explains how to set up and use Hyperledger Indy test network with the Turkey E-License Platform.

## Overview

The platform now supports integration with **Hyperledger Indy**, a distributed ledger purpose-built for decentralized identity. This integration provides:

- **Decentralized Identity Management**: Use DIDs (Decentralized Identifiers) for issuers and holders
- **Verifiable Credentials**: W3C-standard credentials anchored to Indy ledger
- **Revocation Registries**: Cryptographic proof of credential revocation status
- **Interoperability**: Compatible with other Indy-based identity systems

## Quick Start

### ⚡ Super Quick (30 seconds)

**Mock Indy Ledger** - No setup required!

```bash
python api.py
```

The system automatically uses a mock Indy ledger. Perfect for testing!

### 🚀 Real Indy Network (5 minutes)

**Using Von Network** (Recommended):

```bash
# 1. Start Von Network
docker run -d --name von-network -p 9000:8000 -p 9708:9708 -p 9709:9709 \
  ghcr.io/hyperledger/indy-plenum:latest

# 2. Wait 30 seconds, then get genesis transaction
sleep 30
curl http://localhost:9000/genesis > data/genesis.txn

# 3. Start the API
python api.py
```

### 📝 Detailed Setup

For step-by-step instructions, see [VON_NETWORK_SETUP.md](VON_NETWORK_SETUP.md).

##### Option B2: Sovrin StagingNet/BuoyNet
Use Sovrin's public test networks:
- **StagingNet**: For testing (tokens available from faucet)
- **BuoyNet**: For development

##### Option B3: Self-Hosted Indy Network
For production, set up your own Indy network using [indy-node](https://github.com/hyperledger/indy-node).

### 3. Configure Indy Integration

Edit `indy_config.json`:

```json
{
  "indy": {
    "enabled": true,
    "network": "test",  // Options: "test", "local", "production"
    "pool_name": "turkey_elicense_pool",
    "genesis_txn_path": "data/genesis_txn.json",
    "wallet_storage_path": "data/{city_slug}/indy_wallet"
  }
}
```

### 4. Start the Application

```bash
# Start the API server
python api.py

# Or use the CLI
python main.py
```

## How It Works

### Credential Issuance Flow

1. **License Data Validation**: Smart contract validates business rules
2. **Verifiable Credential Creation**: W3C-standard credential is created
3. **Indy Ledger Write**: Credential hash is written to Indy ledger
4. **QR Code Generation**: QR code contains credential for verification
5. **Local Storage**: Full credential stored in local database and IPFS

### Verification Flow

1. **QR Code Scan**: Credential is extracted from QR code
2. **Signature Verification**: Cryptographic signature is verified
3. **Ledger Check**: Credential status checked on Indy ledger
4. **Revocation Check**: Revocation status verified
5. **Result**: Valid/Invalid status returned

## API Endpoints

### Indy-Specific Endpoints

- `GET /api/indy/stats` - Get Indy ledger statistics
- `GET /api/indy/verify/{license_id}` - Verify credential on Indy ledger
- `POST /api/indy/revoke/{license_id}` - Revoke credential on Indy ledger

### Existing Endpoints (Enhanced)

- `POST /api/issue` - Now writes to Indy ledger automatically
- `GET /api/verify/{license_id}` - Now checks Indy ledger
- `GET /api/blockchain` - Shows both local and Indy integration

## Multi-City Support

The system supports all 81 Turkish provinces, each with:
- Unique DID (Decentralized Identifier)
- Separate wallet storage
- Independent schema and credential definitions
- Per-city Indy pool configuration

Example DIDs:
- Konya: `did:indy:tr:konya:municipality`
- Istanbul: `did:indy:tr:istanbul:municipality`
- Ankara: `did:indy:tr:ankara:municipality`

## Security Considerations

### Wallet Security
- Each city has its own secure wallet storage
- Private keys stored in encrypted format
- Wallet access controlled by issuer credentials

### Ledger Security
- Credentials anchored to immutable ledger
- Cryptographic proofs prevent tampering
- Revocation registries provide real-time status

### Network Security
- TLS encryption for network communication
- Authentication required for write operations
- Audit trail of all ledger transactions

## Troubleshooting

### Issue: indy-vdr Installation Fails

**Solution**: Use mock Indy ledger (automatic fallback)
```python
# The system automatically uses mock ledger if indy-vdr is not available
# No action required
```

### Issue: Cannot Connect to Indy Network

**Solution**: Check network configuration
1. Verify `indy_config.json` settings
2. Ensure Indy network is running
3. Check firewall settings
4. Verify genesis transaction file exists

### Issue: Credentials Not Appearing on Ledger

**Solution**: Check issuance process
1. Verify smart contract validation passed
2. Check console output for Indy write errors
3. Ensure wallet is properly initialized
4. Verify network connectivity

## Production Deployment

For production deployment:

1. **Use Real Indy Network**: Set up production Indy network
2. **Secure Wallet Storage**: Use hardware security modules (HSM)
3. **Network Security**: Implement proper TLS and firewall rules
4. **Monitoring**: Set up logging and monitoring for Indy operations
5. **Backup**: Regular backups of wallet storage and ledger data
6. **Disaster Recovery**: Plan for network failures and recovery

## Development Tips

### Testing with Mock Ledger
```python
from utils.indy_ledger import IndyLedgerManager
import asyncio

# The mock ledger is automatically used if indy-vdr is not installed
manager = IndyLedgerManager("konya")
result = asyncio.run(manager.write_credential_to_ledger(credential_data))
```

### Debugging Indy Operations
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Viewing Ledger Data
Access the blockchain explorer:
```
http://localhost:8000/blockchain_explorer.html
```

## Resources

- [Hyperledger Indy Documentation](https://www.hyperledger.org/use/indy)
- [W3C Verifiable Credentials](https://www.w3.org/TR/vc-data-model/)
- [DID Specification](https://www.w3.org/TR/did-core/)
- [indy-vdr Python Bindings](https://github.com/hyperledger/indy-vdr)

## Support

For issues and questions:
- Check the [GitHub repository](https://github.com/SidikaEtci/eruhsat-ssi)
- Review existing issues
- Create new issues with detailed information

## License

This integration follows the same license as the main project.