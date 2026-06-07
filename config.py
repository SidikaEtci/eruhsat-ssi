"""
Configuration for the Turkey e-license platform.
Set CITY_SLUG (e.g. konya, istanbul, ankara) for single-city deployments.
"""
import os
from pathlib import Path

from cities import DEFAULT_CITY_SLUG, get_city, list_city_summaries

# Project paths
BASE_DIR = Path(__file__).parent
DATA_ROOT = BASE_DIR / "data"

# Active city (override with CITY_SLUG environment variable)
CITY_SLUG = os.environ.get("CITY_SLUG", DEFAULT_CITY_SLUG).lower().strip()
ACTIVE_CITY = get_city(CITY_SLUG)

# Per-city data directories (supports multi-city on one instance)
def city_data_dir(city_slug: str | None = None) -> Path:
    slug = (city_slug or CITY_SLUG).lower()
    legacy_files = (DATA_ROOT / "credentials.json", DATA_ROOT / "blockchain_ledger.json")
    if slug == DEFAULT_CITY_SLUG and any(path.exists() for path in legacy_files):
        path = DATA_ROOT
    else:
        path = DATA_ROOT / slug
    for sub in ("keys", "documents", "qr_codes"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_city_slug(license_id: str | None = None, city_slug: str | None = None) -> str:
    """Resolve municipality slug from explicit value or license ID prefix."""
    if city_slug:
        return get_city(city_slug)["slug"]
    if license_id:
        parts = str(license_id).split("-")
        if len(parts) >= 2:
            prefix = parts[1].upper()
            from cities import CITIES

            for city in CITIES.values():
                if city["license_prefix"] == prefix:
                    return city["slug"]
    return CITY_SLUG


# Legacy paths for default city (backward compatible)
DATA_DIR = city_data_dir(CITY_SLUG)
KEYS_DIR = DATA_DIR / "keys"
DOCUMENTS_DIR = DATA_DIR / "documents"
QR_CODES_DIR = DATA_DIR / "qr_codes"

DATA_ROOT.mkdir(exist_ok=True, parents=True)

# Blockchain configuration
GENESIS_TXN_PATH = "/tmp/genesis.txn"
POOL_NAME = ACTIVE_CITY["pool_name"]

# Hyperledger Indy configuration
INDY_ENABLED = True  # Set to False to disable Indy integration
INDY_NETWORK = "test"  # Options: "test", "local", "production"
INDY_POOL_NAME = POOL_NAME

# IPFS configuration
IPFS_HOST = os.environ.get("IPFS_HOST", "127.0.0.1")
IPFS_PORT = int(os.environ.get("IPFS_PORT", "5001"))

# Issuer configuration (from active city)
ISSUER_DID = ACTIVE_CITY["issuer_did"]
ISSUER_NAME = ACTIVE_CITY["issuer_name"]
ISSUER_SEED = ACTIVE_CITY["issuer_seed"]
CREDENTIAL_CONTEXT = ACTIVE_CITY["credential_context"]

# Public app branding
APP_NAME = "Turkey E-License Platform"
CITY_NAME = ACTIVE_CITY["name"]
LICENSE_PREFIX = ACTIVE_CITY["license_prefix"]
LICENSE_ID_EXAMPLE = ACTIVE_CITY["license_id_example"]

# Schema configuration
SCHEMA_NAME = "ELicense"
SCHEMA_VERSION = "1.0"
SCHEMA_ATTRIBUTES = [
    "license_id",
    "license_type",
    "city",
    "issue_date",
    "expiry_date",
    "district",
    "ipfs_hash",
    "document_hash",
]

# Security
ENCRYPTION_SECRET = os.environ.get(
    "ENCRYPTION_SECRET", "turkey_elicense_encryption_secret"
)
AES_KEY_SIZE = 32

# QR Code configuration
QR_VERSION = 10
QR_ERROR_CORRECTION = "H"
QR_BOX_SIZE = 10
QR_BORDER = 4

# API / UI
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")
MULTI_CITY_ENABLED = os.environ.get("MULTI_CITY", "true").lower() in ("1", "true", "yes")


def paths_for_city(city_slug: str) -> dict[str, Path]:
    root = city_data_dir(city_slug)
    return {
        "data_dir": root,
        "keys_dir": root / "keys",
        "documents_dir": root / "documents",
        "qr_codes_dir": root / "qr_codes",
        "credentials": root / "credentials.json",
    }


def settings_payload(city_slug: str | None = None) -> dict:
    city = get_city(city_slug or CITY_SLUG)
    return {
        "app_name": APP_NAME,
        "multi_city": MULTI_CITY_ENABLED,
        "default_city_slug": CITY_SLUG,
        "public_base_url": PUBLIC_BASE_URL,
        "city": {
            "slug": city["slug"],
            "name": city["name"],
            "issuer_name": city["issuer_name"],
            "license_prefix": city["license_prefix"],
            "license_id_example": city["license_id_example"],
            "districts": city["districts"],
            "plate_code": city["plate_code"],
        },
        "cities": list_city_summaries() if MULTI_CITY_ENABLED else [city],
    }
