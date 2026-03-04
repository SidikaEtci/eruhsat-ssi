"""
Quick test script for E-Ruhsat system
"""
from pathlib import Path
from services.issuer import RuhsatIssuer
from services.verifier import RuhsatVerifier


def create_test_pdf():
    """Create a test PDF document"""
    pdf_path = Path("data/documents/test_ruhsat.pdf")
    
    with open(pdf_path, 'w', encoding='utf-8') as f:
        f.write("""
        KONYA BÜYÜKŞEHİR BELEDİYESİ
        
        RESTORAN İŞLETME RUHSATI
        
        Ruhsat No: 2024-KON-TEST-001
        İşletme Sahibi: Test User
        TC Kimlik: 12345678901
        İşletme Türü: Restoran
        Adres: Selçuklu, Konya
        
        Bu belge test amaçlıdır.
        """)
    
    print(f"✅ Test PDF created: {pdf_path}")
    return str(pdf_path)


def test_full_workflow():
    """Test complete workflow"""
    print("\n" + "="*60)
    print("🧪 TESTING COMPLETE E-RUHSAT WORKFLOW")
    print("="*60)
    
    # 1. Create test PDF
    print("\n📄 Step 1: Creating test document...")
    pdf_path = create_test_pdf()
    
    # 2. Initialize services
    print("\n🔧 Step 2: Initializing services...")
    issuer = RuhsatIssuer()
    verifier = RuhsatVerifier()
    
    # 3. Issue ruhsat
    print("\n📜 Step 3: Issuing e-ruhsat...")
    ruhsat_data = {
        'ruhsat_no': '2024-KON-TEST-001',
        'ruhsat_turu': 'Restoran Isletme Ruhsati',
        'ad_soyad': 'Ahmet Test',
        'tc_kimlik': '12345678901',
        'bolge': 'Selcuklu',
        'verilme_tarihi': '2024-01-01',
        'gecerlilik_tarihi': '2025-01-01',
    }
    
    result = issuer.issue_ruhsat(ruhsat_data, pdf_path)
    
    if not result['success']:
        print("❌ Failed to issue ruhsat")
        return
    
    # 4. Verify offline
    print("\n🔍 Step 4: Testing offline verification...")
    
    # Reconstruct QR data for verification
    import json
    from utils.crypto import CryptoManager
    
    qr_public_data = {
        'ruhsat_no': ruhsat_data['ruhsat_no'],
        'ruhsat_turu': ruhsat_data['ruhsat_turu'],
        'belediye': ruhsat_data['belediye'],
        'verilme_tarihi': ruhsat_data['verilme_tarihi'],
        'gecerlilik_tarihi': ruhsat_data['gecerlilik_tarihi'],
        'bolge': ruhsat_data['bolge'],
        'durum': 'Gecerli'
    }
    
    signature = CryptoManager.sign_data(qr_public_data, issuer.private_key)
    
    qr_payload = {
        "version": "1.0",
        "offline_data": qr_public_data,
        "signature": signature,
        "signed_by": "did:indy:konya:KBB",
        "online_refs": {
            "ipfs_hash": result.get('ipfs_hash', ''),
            "document_hash": ruhsat_data.get('document_hash', ''),
        }
    }
    
    qr_data_string = json.dumps(qr_payload)
    
    offline_result = verifier.verify_offline(qr_data_string)
    
    if offline_result['valid']:
        print("✅ Offline verification: PASSED")
    else:
        print("❌ Offline verification: FAILED")
    
    # 5. Verify online
    print("\n🔍 Step 5: Testing online verification...")
    online_result = verifier.verify_online(qr_data_string)
    
    if online_result['valid']:
        print("✅ Online verification: PASSED")
    else:
        print("❌ Online verification: FAILED")
    
    # 6. Test revocation
    print("\n🚫 Step 6: Testing revocation...")
    issuer.revoke_ruhsat('2024-KON-TEST-001')
    
    # Verify after revocation
    revoked_result = verifier.verify_online(qr_data_string)
    
    if not revoked_result['valid']:
        print("✅ Revocation check: PASSED (correctly rejected)")
    else:
        print("❌ Revocation check: FAILED (should be rejected)")
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"✅ PDF Creation: Success")
    print(f"✅ Ruhsat Issuance: Success")
    print(f"✅ Offline Verification: {'Success' if offline_result['valid'] else 'Failed'}")
    print(f"✅ Online Verification: {'Success' if online_result['valid'] else 'Failed'}")
    print(f"✅ Revocation: {'Success' if not revoked_result['valid'] else 'Failed'}")
    print("\n✨ All tests completed!")


if __name__ == "__main__":
    test_full_workflow()
