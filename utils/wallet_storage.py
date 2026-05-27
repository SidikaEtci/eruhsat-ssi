"""
JSON persistence for MetaMask wallet records, credential offers, and challenges.
"""
import json
from datetime import datetime
from pathlib import Path

import config

WALLETS_DIR = config.DATA_ROOT / "wallets"
WALLETS_DIR.mkdir(parents=True, exist_ok=True)
CHALLENGES_FILE = config.DATA_ROOT / "wallet_challenges.json"


def _wallet_path(address: str) -> Path:
    return WALLETS_DIR / f"{address.lower()}.json"


def _load_challenges() -> dict:
    if not CHALLENGES_FILE.exists():
        return {}
    try:
        with open(CHALLENGES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}


def _save_challenges(data: dict) -> None:
    with open(CHALLENGES_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def get_wallet(address: str) -> dict | None:
    path = _wallet_path(address)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_wallet(address: str, wallet_data: dict) -> None:
    with open(_wallet_path(address), "w", encoding="utf-8") as file:
        json.dump(wallet_data, file, indent=2, ensure_ascii=False)


def add_pending_offer(address: str, offer: dict) -> bool:
    wallet = get_wallet(address)
    if not wallet:
        return False
    wallet.setdefault("pending_offers", []).append(offer)
    save_wallet(address, wallet)
    return True


def get_pending_offers(address: str) -> list:
    wallet = get_wallet(address)
    return wallet.get("pending_offers", []) if wallet else []


def accept_pending_offer(address: str, offer_id: str) -> dict | None:
    wallet = get_wallet(address)
    if not wallet:
        return None

    for index, offer in enumerate(wallet.get("pending_offers", [])):
        if offer.get("offer_id") != offer_id:
            continue
        credential = offer["credential"]
        credential["stored_at"] = datetime.now().isoformat() + "Z"
        wallet.setdefault("credentials", []).append(credential)
        wallet["pending_offers"].pop(index)
        save_wallet(address, wallet)
        return {"license_id": offer.get("license_id"), "credential": credential}

    return None


def get_credentials(address: str) -> list:
    wallet = get_wallet(address)
    return wallet.get("credentials", []) if wallet else []


def get_credential(address: str, license_id: str) -> dict | None:
    for credential in get_credentials(address):
        subject = credential.get("credentialSubject", {})
        if subject.get("licenseId") == license_id:
            return credential
    return None


def store_challenge(challenge_id: str, challenge: dict) -> None:
    challenges = _load_challenges()
    challenges[challenge_id] = challenge
    _save_challenges(challenges)


def consume_challenge(challenge_id: str) -> dict | None:
    challenges = _load_challenges()
    challenge = challenges.pop(challenge_id, None)
    if challenge is not None:
        _save_challenges(challenges)
    return challenge
