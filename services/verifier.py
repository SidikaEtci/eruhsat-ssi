import os
import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from utils.ipfs_manager import IPFSManager

class LicenseVerifier:
    def __init__(self, keys_dir="data/keys"):
        """
        Initializes the License Verifier with the public key path and IPFS manager.
        """
        self.keys_dir = keys_dir
        self.public_key_path = os.path.join(self.keys_dir, "issuer_public_key.pem")
        self.ipfs_manager = IPFSManager()
        self.public_key = self._load_public_key()

    def _load_public_key(self):
        """
        Loads the Issuer's RSA public key from the local disk.
        """
        if os.path.exists(self.public_key_path):
            try:
                with open(self.public_key_path, "rb") as key_file:
                    return serialization.load_pem_public_key(key_file.read())
            except Exception as e:
                print(f"Error loading public key: {str(e)}")
                return None
        else:
            print(f"Warning: Public key file not found at {self.public_key_path}")
            return None

    def verify_credential(self, credential: dict) -> bool:
        """
        Verifies a W3C compliant Verifiable Credential using the signature embedded inside its proof block.
        """
        if not self.public_key:
            print("Verification failed: Public key is not loaded.")
            return False

        if "proof" not in credential or "jws" not in credential["proof"]:
            print("Verification failed: Credential does not contain a valid W3C proof block.")
            return False

        try:
            # 1. Extract the signature (JWS) from the proof block
            proof = credential["proof"]
            signature_b64 = proof["jws"]
            signature = base64.b64decode(signature_b64)

            # 2. Create a copy of the credential and remove the proof block to get the original un-signed content
            credential_copy = json.loads(json.dumps(credential))
            credential_copy.pop("proof", None)

            # 3. Serialize the exact data that was hashed during the issuance process
            serialized_data = json.dumps(credential_copy, sort_keys=True).encode('utf-8')

            # 4. Perform cryptographic verification using the public key
            self.public_key.verify(
                signature,
                serialized_data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"Cryptographic verification failed: {str(e)}")
            return False

    def verify_from_ipfs(self, ipfs_hash: str) -> dict:
        """
        Fetches the Verifiable Credential from IPFS via its CID and verifies its integrity.
        """
        # Fetch JSON content from decentralized storage
        credential = self.ipfs_manager.download_json(ipfs_hash)
        if not credential:
            return {"status": "Failed", "message": "Could not retrieve credential from IPFS"}

        # Validate the inner signature block
        is_valid = self.verify_credential(credential)
        
        if is_valid:
            return {
                "status": "Success",
                "message": "Credential successfully verified via IPFS data layer.",
                "data": credential.get("credentialSubject", {})
            }
        else:
            return {"status": "Failed", "message": "IPFS data signature verification failed."}

    def verify_offline(self, credential_json_str: str) -> dict:
        """
        Performs an offline verification on a raw JSON string extracted from a QR code or user input.
        """
        try:
            credential = json.loads(credential_json_str)
            is_valid = self.verify_credential(credential)
            
            if is_valid:
                return {
                    "status": "Success",
                    "message": "Offline cryptographic signature is valid.",
                    "data": credential.get("credentialSubject", {})
                }
            else:
                return {"status": "Failed", "message": "Offline signature verification failed."}
        except json.JSONDecodeError:
            return {"status": "Failed", "message": "Invalid JSON format provided for offline verification."}