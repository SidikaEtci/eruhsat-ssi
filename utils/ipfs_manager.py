"""IPFS Manager — hybrid RSA+AES encryption via AsymmetricCrypto"""
import ipfshttpclient
from pathlib import Path
from cryptography.hazmat.primitives import serialization

import config
from utils.crypto import CryptoManager, AsymmetricCrypto

PUBLIC_KEY_PATH  = Path('data/keys/public_key.pem')
PRIVATE_KEY_PATH = Path('data/keys/private_key.pem')


class IPFSManager:
    def __init__(self):
        try:
            self.client = ipfshttpclient.connect(
                f'/ip4/{config.IPFS_HOST}/tcp/{config.IPFS_PORT}/http'
            )
            print(f"   Connected to IPFS at {config.IPFS_HOST}:{config.IPFS_PORT}")
        except Exception as e:
            print(f"   IPFS Connection Failed: {e}")
            print("   Start IPFS: ipfs daemon")
            raise

    def _load_public_key(self):
        with open(PUBLIC_KEY_PATH, 'rb') as f:
            return serialization.load_pem_public_key(f.read())

    def _load_private_key(self):
        with open(PRIVATE_KEY_PATH, 'rb') as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    def upload_encrypted_document(self, file_path: str, license_id: str) -> dict:
        """Encrypt with RSA hybrid and upload to IPFS."""
        print(f"\n   IPFS Upload starting: {file_path}")

        original_hash = CryptoManager.calculate_hash(file_path)
        print(f"   Original hash: {original_hash[:16]}...")

        with open(file_path, 'rb') as f:
            data = f.read()

        encrypted_data = AsymmetricCrypto.encrypt_document(data, self._load_public_key())
        print(f"   Encrypted ({len(encrypted_data)} bytes)")

        temp_file = Path(config.DOCUMENTS_DIR) / f"{license_id}.encrypted"
        temp_file.write_bytes(encrypted_data)
        print(f"   Temporary file saved")

        try:
            print(f"   Uploading to IPFS...")
            result = self.client.add(str(temp_file))
            ipfs_hash = result['Hash']
            print(f"   IPFS Hash: {ipfs_hash}")
        except Exception as e:
            print(f"   IPFS Upload Failed: {e}")
            raise
        finally:
            temp_file.unlink(missing_ok=True)

        return {
            'ipfs_hash': ipfs_hash,
            'document_hash': original_hash,
            'file_size': len(encrypted_data),
            'gateway_url': f"https://ipfs.io/ipfs/{ipfs_hash}"
        }

    def verify_file_exists(self, ipfs_hash: str) -> bool:
        """Check if file exists on IPFS."""
        try:
            stat = self.client.object.stat(ipfs_hash)
            print(f"   File exists on IPFS: {ipfs_hash} ({stat['CumulativeSize']} bytes)")
            return True
        except Exception as e:
            print(f"   File not found on IPFS: {e}")
            return False

    def download_and_decrypt(self, ipfs_hash: str, license_id: str, output_path: str) -> bool:
        """Download from IPFS and decrypt with RSA private key."""
        try:
            print(f"\n   Downloading from IPFS: {ipfs_hash}")

            docs_dir = Path(config.DOCUMENTS_DIR)
            temp_encrypted = docs_dir / f"{ipfs_hash}.encrypted"
            downloaded    = docs_dir / ipfs_hash

            # Clear any leftovers from a previous failed attempt
            temp_encrypted.unlink(missing_ok=True)
            downloaded.unlink(missing_ok=True)

            self.client.get(ipfs_hash, target=str(docs_dir))

            if not downloaded.exists():
                raise FileNotFoundError(f"IPFS download produced no file at {downloaded}")

            downloaded.rename(temp_encrypted)
            print(f"   Downloaded ({temp_encrypted.stat().st_size} bytes)")

            print(f"   Decrypting...")
            encrypted_bytes = temp_encrypted.read_bytes()
            decrypted = AsymmetricCrypto.decrypt_document(encrypted_bytes, self._load_private_key())

            Path(output_path).write_bytes(decrypted)
            print(f"   Saved: {output_path}")
            return True

        except Exception as e:
            import traceback
            print(f"   Download/Decrypt failed: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

        finally:
            temp_encrypted.unlink(missing_ok=True)
