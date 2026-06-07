# eruhsat-ssi

Turkey Municipal E-License Platform with Hyperledger Indy Integration.

## Overview

A blockchain-based digital license management system for Turkish municipalities, featuring:

- **Hyperledger Indy Integration**: Decentralized identity and verifiable credentials
- **Multi-City Support**: All 81 Turkish provinces with independent configurations
- **Smart Contracts**: Business rule enforcement and validation
- **IPFS Storage**: Decentralized document storage
- **QR Code Verification**: Offline-capable credential verification
- **W3C Standards**: Verifiable Credentials and DIDs compliance

## Features

### Core Features
- ✅ Issue digital business licenses
- ✅ QR code generation and verification
- ✅ IPFS document storage
- ✅ Blockchain ledger (local + Indy)
- ✅ Smart contract enforcement
- ✅ Multi-city support (81 provinces)
- ✅ Revocation management
- ✅ Cryptographic security

### Hyperledger Indy Integration
- ✅ Decentralized Identifiers (DIDs)
- ✅ Verifiable Credentials (W3C standard)
- ✅ Ledger anchoring
- ✅ Revocation registries
- ✅ Mock ledger for development
- ✅ Real network support

## Quick Start

### ⚡ Fastest Way (30 seconds)

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API
python api.py
```

That's it! The system includes a mock Indy ledger for testing - no setup required.

### 🚀 With Real Indy Network (5 minutes)

```bash
# 1. Start Von Network (Indy blockchain)
docker run -d --name von-network -p 9000:8000 -p 9708:9708 -p 9709:9709 \
  ghcr.io/hyperledger/indy-plenum:latest

# 2. Wait 30 seconds, then get genesis transaction
sleep 30
curl http://localhost:9000/genesis > data/genesis.txn

# 3. Start the API
python api.py
```

### 📋 Full Installation

1. **Clone the repository**
```bash
git clone https://github.com/SidikaEtci/eruhsat-ssi.git
cd eruhsat-ssi
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up Hyperledger Indy (Optional)**
```bash
python setup_indy_network.py
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Start the application**

**Option A: API Server**
```bash
python api.py
```
Visit: http://localhost:8000

**Option B: CLI Application**
```bash
python main.py
```

**Option C: Docker (with Indy network)**
```bash
docker-compose -f docker-compose.indy.yml up
```

### 🧪 Testing

```bash
# Run automated tests
python test_indy.py

# Or test manually:
# 1. Open http://localhost:8000
# 2. Issue a test license
# 3. Check console for "✓ Credential written to Hyperledger Indy"
```

## Usage

### Web Interface
- **Main Page**: http://localhost:8000
- **Blockchain Explorer**: http://localhost:8000/blockchain_explorer.html
- **IPFS Explorer**: http://localhost:8000/ipfs_explorer.html
- **API Docs**: http://localhost:8000/docs

### API Endpoints

#### License Management
- `POST /api/issue` - Issue new license
- `GET /api/verify/{license_id}` - Verify license
- `GET /api/licenses` - List all licenses
- `GET /api/qr/{license_id}` - Get QR code

#### Blockchain
- `GET /api/blockchain` - Get blockchain ledger
- `GET /api/indy/stats` - Get Indy statistics
- `GET /api/indy/verify/{license_id}` - Verify on Indy
- `POST /api/indy/revoke/{license_id}` - Revoke on Indy

#### System
- `GET /api/settings` - Get application settings
- `GET /api/health` - Health check
- `POST /api/login` - User authentication

### CLI Commands

```
1. Issue new license
2. Verify license
3. Get license info
4. Change municipality
5. Exit
```

## Architecture

### Components

1. **LicenseIssuer** (`services/issuer.py`)
   - Main service for issuing licenses
   - Coordinates between contract, blockchain, and storage

2. **LicenseContract** (`contracts/license_contract.py`)
   - Smart contract with business rules
   - Validation and enforcement
   - Encrypted ledger storage

3. **BlockchainLogger** (`utils/blockchain_logger.py`)
   - Local blockchain ledger
   - Block creation and verification
   - Per-city ledgers

4. **IndyLedgerManager** (`utils/indy_ledger.py`)
   - Hyperledger Indy integration
   - Credential writing and verification
   - Mock and real network support

5. **VerifiableCredentialManager** (`utils/verifiable_credentials.py`)
   - W3C Verifiable Credentials
   - Cryptographic proofs
   - DID management

### Data Flow

```
License Application
    ↓
Smart Contract Validation
    ↓
Verifiable Credential Creation
    ↓
Indy Ledger Write (or Mock)
    ↓
Local Blockchain Write
    ↓
IPFS Document Storage
    ↓
QR Code Generation
    ↓
Database Storage
```

## Multi-City Support

The system supports all 81 Turkish provinces. Each city has:
- Unique DID (Decentralized Identifier)
- Independent wallet storage
- Custom license ID prefix
- Per-city districts
- Separate blockchain ledger

Example cities:
- Konya (Default): `did:indy:tr:konya:municipality`
- Istanbul: `did:indy:tr:istanbul:municipality`
- Ankara: `did:indy:tr:ankara:municipality`

## Hyperledger Indy Integration

### Mock vs Real Ledger

**Mock Ledger (Development)**
- Automatic fallback when indy-vdr not installed
- No external dependencies
- Perfect for testing and development
- Same API as real ledger

**Real Indy Network (Production)**
- Full decentralized identity features
- Interoperability with other Indy systems
- Production-grade security
- Requires Indy network setup

### Setup Instructions

See [INDY_SETUP.md](INDY_SETUP.md) for detailed setup instructions.

### Quick Indy Setup

```bash
# Run setup script
python setup_indy_network.py

# For real Indy network, use Docker
docker-compose -f docker-compose.indy.yml up

# Or configure manually in indy_config.json
```

## Security

- **Cryptography**: RSA-2048/AES-GCM-256 encryption
- **Digital Signatures**: Ed25519Signature2020
- **Blockchain**: Immutable ledger with hash chaining
- **Indy Integration**: Decentralized trust anchor
- **Access Control**: Role-based authentication

## Configuration

### Environment Variables

```bash
# City Configuration
CITY_SLUG=konya  # Default city

# Multi-City Support
MULTI_CITY=true  # Enable city selection

# Public URL
PUBLIC_BASE_URL=http://localhost:8000

# IPFS Configuration
IPFS_HOST=127.0.0.1
IPFS_PORT=5001

# Indy Configuration
INDY_ENABLED=true
INDY_NETWORK=test
```

### Configuration Files

- `.env` - Environment variables
- `indy_config.json` - Indy network configuration
- `cities.py` - City definitions and metadata

## Development

### Project Structure

```
├── api.py                 # FastAPI application
├── main.py               # CLI application
├── config.py             # Configuration management
├── cities.py             # City registry
│
├── contracts/
│   └── license_contract.py  # Smart contract
│
├── services/
│   └── issuer.py            # License issuer service
│
├── utils/
│   ├── blockchain_logger.py # Local blockchain
│   ├── indy_ledger.py       # Indy integration
│   ├── verifiable_credentials.py
│   ├── ipfs_manager.py
│   ├── qr_generator.py
│   ├── crypto.py
│   └── auth.py
│
├── web/                    # Web interface
│   ├── index.html
│   ├── blockchain_explorer.html
│   ├── verify_qr.html
│   └── ...
│
├── data/                   # Data storage
│   ├── blockchain_ledger.json
│   ├── users.json
│   └── {city_slug}/        # Per-city data
│
└── tests/                  # Test suite
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_issuer.py
```

### Adding New Cities

Edit `cities.py` to add new municipalities:

```python
CITIES = {
    # ... existing cities
    "newcity": {
        "slug": "newcity",
        "name": "New City",
        "plate_code": "99",
        "license_prefix": "NEW",
        "metropolitan": False,
        "districts": ["District 1", "District 2"],
        "issuer_name": "New City Municipality",
        "issuer_did": "did:indy:tr:newcity:municipality",
        "issuer_seed": "newcity_municipality_license_seed",
        "credential_context": "https://newcity.bel.tr/credentials/v1",
        "pool_name": "newcity_pool",
    }
}
```

## Deployment

### Production Considerations

1. **Database**: Use PostgreSQL instead of JSON files
2. **Caching**: Implement Redis for performance
3. **Load Balancing**: Use Nginx or HAProxy
4. **Monitoring**: Set up Prometheus and Grafana
5. **Security**: Enable HTTPS and security headers
6. **Backup**: Regular database and wallet backups

### Docker Deployment

```bash
# Build and run with Docker
docker build -t eruhsat-ssi .
docker run -p 8000:8000 eruhsat-ssi

# Or use docker-compose
docker-compose up
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests (to be added).

## Troubleshooting

### Common Issues

**Issue**: Cannot install indy-vdr
**Solution**: Use mock ledger (automatic fallback)

**Issue**: Port 8000 already in use
**Solution**: Change port in api.py or use different port

**Issue**: IPFS connection failed
**Solution**: Start IPFS daemon or disable IPFS in config

**Issue**: Database file corrupted
**Solution**: Delete JSON files and restart (data will be recreated)

### Logs and Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

View logs:
```bash
# Console output
# Or check application logs
tail -f /var/log/eruhsat.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/SidikaEtci/eruhsat-ssi/issues)
- **Documentation**: [INDY_SETUP.md](INDY_SETUP.md) for Indy integration
- **API Docs**: http://localhost:8000/docs (when running)

## Acknowledgments

- Hyperledger Indy community
- W3C Credentials Community Group
- Turkish municipalities for requirements and feedback

## Version

Current version: 3.0.0 (with Hyperledger Indy integration)