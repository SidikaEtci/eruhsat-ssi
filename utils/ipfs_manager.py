"""IPFS Manager for encrypted document storage"""
import ipfshttpclient
from pathlib import Path
import config
from utils.crypto import CryptoManager

class IPFSManager:
    def __init__(self):
        try:
            self.client = ipfshttpclient.connect(
                f'/ip4/{config.IPFS_HOST}/tcp/{config.IPFS_PORT}/http'
            )
            print(f"✅ Connected to IPFS at {config.IPFS_HOST}:{config.IPFS_PORT}")
        except Exception as e:
            print(f"❌ IPFS Connection Failed: {e}")
            raise

    def upload_encrypted_document(self, file_path: str, license_id: str) -> dict:
        """Encrypt and upload to IPFS using English keys"""
        encryption_key = CryptoManager.generate_encryption_key(license_id)
        original_hash = CryptoManager.calculate_hash(file_path)
        encrypted_data = CryptoManager.encrypt_file(file_path, encryption_key)

        # Save temporary encrypted file
        temp_file = Path(config.DOCUMENTS_DIR) / f"{license_id}.encrypted"
        with open(temp_file, 'wb') as f:
            f.write(encrypted_data)

        # Upload to IPFS
        result = self.client.add(str(temp_file))
        temp_file.unlink() # Cleanup

        return {
            'ipfs_hash': result['Hash'],
            'document_hash': original_hash,
            'file_size': len(encrypted_data)
        }