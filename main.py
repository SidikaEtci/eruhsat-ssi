"""
Konya E-Ruhsat System - Main Application
"""
import sys
from pathlib import Path
from services.issuer import RuhsatIssuer
from services.verifier import RuhsatVerifier


def print_menu():
    """Print main menu"""
    print("\n" + "="*60)
    print("🏛️  KONYA E-RUHSAT SYSTEM")
    print("="*60)
    print("\n1. Issue new ruhsat")
    print("2. Verify ruhsat (offline)")
    print("3. Verify ruhsat (online)")
    print("4. Verify ruhsat (authority - full access)")
    print("5. Revoke ruhsat")
    print("6. Get ruhsat info")
    print("7. Exit")
    print("\n" + "="*60)


def issue_ruhsat_interactive(issuer: RuhsatIssuer):
    """Interactive ruhsat issuance"""
    print("\n📜 ISSUE NEW E-RUHSAT")
    print("-" * 60)
    
    # Get ruhsat data
    ruhsat_data = {
        'ruhsat_no': input("Ruhsat Number (e.g., 2024-KON-001): ").strip(),
        'ruhsat_turu': input("Ruhsat Type (e.g., Restoran Isletme): ").strip(),
        'ad_soyad': input("Owner Name: ").strip(),
        'tc_kimlik': input("TC Kimlik No: ").strip(),
        'bolge': input("District/Area (e.g., Selcuklu): ").strip(),
        'verilme_tarihi': input("Issue Date (YYYY-MM-DD): ").strip(),
        'gecerlilik_tarihi': input("Expiry Date (YYYY-MM-DD): ").strip(),
    }
    
    # Ask for PDF
    pdf_path = input("PDF Path (press Enter to skip): ").strip()
    
    if not pdf_path:
        pdf_path = None
    elif not Path(pdf_path).exists():
        print(f"⚠️  PDF file not found: {pdf_path}")
        pdf_path = None
    
    # Issue ruhsat
    try:
        result = issuer.issue_ruhsat(ruhsat_data, pdf_path)
        
        if result['success']:
            print(f"\n✅ Ruhsat issued successfully!")
            print(f"📱 QR Code saved at: {result['qr_code_path']}")
            
            # Ask to view QR code
            view = input("\nOpen QR code image? (y/n): ").strip().lower()
            if view == 'y':
                import os
                os.system(f"xdg-open {result['qr_code_path']}")
    
    except Exception as e:
        print(f"\n❌ Error issuing ruhsat: {e}")


def verify_ruhsat_interactive(verifier: RuhsatVerifier, mode: str):
    """Interactive ruhsat verification"""
    print(f"\n🔍 VERIFY E-RUHSAT ({mode.upper()})")
    print("-" * 60)
    
    # For demo, we'll read QR data from a saved file
    # In real app, this would come from QR scanner
    
    ruhsat_no = input("Enter Ruhsat Number to verify: ").strip()
    
    # Find QR code file
    qr_file = Path(f"data/qr_codes/{ruhsat_no}.png")
    
    if not qr_file.exists():
        print(f"❌ QR code not found for: {ruhsat_no}")
        return
    
    # For demo, we'll reconstruct the QR data from database
    # In real app, you'd scan the actual QR code
    
    print(f"📱 Reading QR code from: {qr_file}")
    
    # Load credential from database to get QR data
    import json
    db_path = Path("data/credentials.json")
    
    if not db_path.exists():
        print("❌ No credentials database found")
        return
    
    with open(db_path, 'r', encoding='utf-8') as f:
        credentials_db = json.load(f)
    
    credential = None
    for cred in credentials_db:
        if cred['ruhsat_no'] == ruhsat_no:
            credential = cred
            break
    
    if not credential:
        print(f"❌ Credential not found: {ruhsat_no}")
        return
    
    # Reconstruct QR data (in real app, this comes from scanning)
    from utils.crypto import CryptoManager
    from services.issuer import RuhsatIssuer
    
    # Need issuer to sign (for demo purposes)
    issuer = RuhsatIssuer()
    
    qr_public_data = {
        'ruhsat_no': credential['ruhsat_no'],
        'ruhsat_turu': credential['ruhsat_turu'],
        'belediye': credential['belediye'],
        'verilme_tarihi': credential['verilme_tarihi'],
        'gecerlilik_tarihi': credential['gecerlilik_tarihi'],
        'bolge': credential['bolge'],
        'durum': 'Gecerli' if credential['status'] == 'active' else 'Iptal'
    }
    
    signature = CryptoManager.sign_data(qr_public_data, issuer.private_key)
    
    qr_payload = {
        "version": "1.0",
        "type": "konya_eruhsat",
        "offline_data": qr_public_data,
        "signature": signature,
        "signed_by": "did:indy:konya:KBB",
        "online_refs": {
            "ipfs_hash": credential.get('ipfs_hash', ''),
            "document_hash": credential.get('document_hash', ''),
        }
    }
    
    qr_data_string = json.dumps(qr_payload)
    
    # Verify based on mode
    try:
        if mode == 'offline':
            result = verifier.verify_offline(qr_data_string)
        elif mode == 'online':
            result = verifier.verify_online(qr_data_string)
        elif mode == 'authority':
            download = input("Download PDF document? (y/n): ").strip().lower() == 'y'
            result = verifier.verify_with_authority(qr_data_string, download_pdf=download)
        
        print(f"\n📊 Verification Result:")
        print(f"   Status: {result['message']}")
        
        if result.get('pdf_path'):
            print(f"   PDF: {result['pdf_path']}")
            
            view = input("\nOpen PDF? (y/n): ").strip().lower()
            if view == 'y':
                import os
                os.system(f"xdg-open {result['pdf_path']}")
    
    except Exception as e:
        print(f"\n❌ Verification error: {e}")


def main():
    """Main application loop"""
    print("\n🚀 Starting Konya E-Ruhsat System...")
    
    # Initialize services
    try:
        issuer = RuhsatIssuer()
        verifier = RuhsatVerifier()
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        return
    
    # Main loop
    while True:
        print_menu()
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == '1':
            issue_ruhsat_interactive(issuer)
        
        elif choice == '2':
            verify_ruhsat_interactive(verifier, 'offline')
        
        elif choice == '3':
            verify_ruhsat_interactive(verifier, 'online')
        
        elif choice == '4':
            verify_ruhsat_interactive(verifier, 'authority')
        
        elif choice == '5':
            ruhsat_no = input("Enter Ruhsat Number to revoke: ").strip()
            issuer.revoke_ruhsat(ruhsat_no)
        
        elif choice == '6':
            ruhsat_no = input("Enter Ruhsat Number: ").strip()
            info = issuer.get_ruhsat_info(ruhsat_no)
            if info:
                import json
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                print("❌ Ruhsat not found")
        
        elif choice == '7':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
