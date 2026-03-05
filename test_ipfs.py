"""Test IPFS upload and verification"""
from pathlib import Path
from utils.ipfs_manager import IPFSManager

def test_ipfs():
    print("\n" + "="*60)
    print("🧪 TESTING IPFS UPLOAD & VERIFICATION")
    print("="*60)
    
    # 1. Create test file
    test_file = Path("data/documents/test_upload.txt")
    test_file.parent.mkdir(exist_ok=True, parents=True)
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("Test document for IPFS upload verification.\n")
        f.write("License ID: TEST-001\n")
        f.write("This is encrypted and uploaded to IPFS.\n")
    
    print(f"✅ Test file created: {test_file}")
    
    # 2. Initialize IPFS
    try:
        ipfs = IPFSManager()
    except Exception as e:
        print(f"\n❌ IPFS not running!")
        print(f"💡 Start IPFS daemon first:")
        print(f"   ipfs daemon")
        return
    
    # 3. Upload
    try:
        result = ipfs.upload_encrypted_document(str(test_file), "TEST-001")
        
        print(f"\n" + "="*60)
        print(f"📊 UPLOAD RESULT:")
        print(f"="*60)
        print(f"IPFS Hash: {result['ipfs_hash']}")
        print(f"Document Hash: {result['document_hash']}")
        print(f"File Size: {result['file_size']} bytes")
        print(f"Gateway URL: {result['gateway_url']}")
        
        # 4. Verify
        print(f"\n🔍 Verifying upload...")
        exists = ipfs.verify_file_exists(result['ipfs_hash'])
        
        if exists:
            print(f"\n✅ IPFS UPLOAD VERIFIED!")
        else:
            print(f"\n❌ IPFS VERIFICATION FAILED!")
        
        # 5. Test download
        print(f"\n📥 Testing download and decrypt...")
        output_file = Path("data/documents/test_download.txt")
        success = ipfs.download_and_decrypt(
            result['ipfs_hash'],
            "TEST-001",
            str(output_file)
        )
        
        if success:
            print(f"\n✅ DOWNLOAD & DECRYPT SUCCESS!")
            print(f"   Check file: {output_file}")
        else:
            print(f"\n❌ DOWNLOAD FAILED!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    test_ipfs()
