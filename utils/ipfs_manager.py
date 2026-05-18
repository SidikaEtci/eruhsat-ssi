"""IPFS Manager with upload verification"""
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
            print(f"   Connected to IPFS at {config.IPFS_HOST}:{config.IPFS_PORT}")
        except Exception as e:
            print(f"   IPFS Connection Failed: {e}")
            print("  Start IPFS: ipfs daemon")
            raise

    def upload_encrypted_document(self, file_path: str, license_id: str) -> dict:
        """Encrypt and upload to IPFS with verification"""
        
        print(f"\n  IPFS Upload Process Starting...")
        print(f"   File: {file_path}")
        
        # 1. Generate encryption key
        encryption_key = CryptoManager.generate_encryption_key(license_id)
        print(f"   Encryption key generated")
        
        # 2. Calculate original hash
        original_hash = CryptoManager.calculate_hash(file_path)
        print(f"   Original hash: {original_hash[:16]}...")
        
        # 3. Encrypt file
        encrypted_data = CryptoManager.encrypt_file(file_path, encryption_key)
        print(f"   File encrypted ({len(encrypted_data)} bytes)")
        
        # 4. Save temporary encrypted file
        temp_file = Path(config.DOCUMENTS_DIR) / f"{license_id}.encrypted"
        with open(temp_file, 'wb') as f:
            f.write(encrypted_data)
        print(f"   Temporary file saved: {temp_file}")
        
        # 5. Upload to IPFS
        print(f"  Uploading to IPFS...")
        try:
            result = self.client.add(str(temp_file))
            ipfs_hash = result['Hash']
            print(f"   IPFS Upload Success!")
            print(f"   IPFS Hash: {ipfs_hash}")
        except Exception as e:
            print(f"   IPFS Upload Failed: {e}")
            temp_file.unlink()
            raise
        
        # 6. Verify upload
        print(f"  Verifying upload...")
        try:
            stat = self.client.object.stat(ipfs_hash)
            print(f"   Verification Success!")
            print(f"   Size on IPFS: {stat['CumulativeSize']} bytes")
            print(f"   Local size: {len(encrypted_data)} bytes")
            
            # Check if accessible
            gateway_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
            print(f"  Gateway URL: {gateway_url}")
            
        except Exception as e:
            print(f" ️  Verification warning: {e}")
            print(f"   File uploaded but verification failed")
        
        # 7. Cleanup
        temp_file.unlink()
        print(f"  Temporary file cleaned up")
        
        return {
            'ipfs_hash': ipfs_hash,
            'document_hash': original_hash,
            'file_size': len(encrypted_data),
            'gateway_url': f"https://ipfs.io/ipfs/{ipfs_hash}"
        }
    
    def verify_file_exists(self, ipfs_hash: str) -> bool:
        """Check if file exists on IPFS"""
        try:
            stat = self.client.object.stat(ipfs_hash)
            print(f"   File exists on IPFS: {ipfs_hash}")
            print(f"   Size: {stat['CumulativeSize']} bytes")
            return True
        except Exception as e:
            print(f"   File not found on IPFS: {e}")
            return False
    
    def download_and_decrypt(self, ipfs_hash: str, license_id: str, output_path: str) -> bool:
        """Download and decrypt with verification"""
        try:
            print(f"\n  Downloading from IPFS: {ipfs_hash}")
            
            # 1. Download
            temp_encrypted = Path(config.DOCUMENTS_DIR) / f"{ipfs_hash}.encrypted"
            self.client.get(ipfs_hash, target=str(temp_encrypted.parent))
            
            downloaded_file = Path(config.DOCUMENTS_DIR) / ipfs_hash
            if downloaded_file.exists():
                downloaded_file.rename(temp_encrypted)
            
            print(f"   Downloaded from IPFS")
            
            # 2. Decrypt
            encryption_key = CryptoManager.generate_encryption_key(license_id)
            
            with open(temp_encrypted, 'rb') as f:
                encrypted_data = f.read()
            
            print(f"  Decrypting...")
            from cryptography.fernet import Fernet
            cipher = Fernet(encryption_key)
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # 3. Save
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            print(f"   Decrypted and saved: {output_path}")
            
            # 4. Cleanup
            temp_encrypted.unlink()
            
            return True
            
        except Exception as e:
            print(f"   Download/Decrypt failed: {e}")
            return False