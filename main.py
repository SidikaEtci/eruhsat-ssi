"""
Konya E-Ruhsat System - Main Application
"""
import sys
from pathlib import Path
from services.issuer import LicenseIssuer


def print_menu():
    """Print main menu"""
    print("\n" + "="*60)
    print("  KONYA E-LICENSE SYSTEM")
    print("="*60)
    print("\n1. Issue new license")
    print("2. Verify license")
    print("3. Get license info")
    print("4. Exit")
    print("\n" + "="*60)


def issue_license_interactive(issuer: LicenseIssuer):
    """Interactive license issuance"""
    print("\n  ISSUE NEW LICENSE")
    print("-" * 60)
    
    # Get license data
    license_data = {
        'license_id': input("License ID (e.g., 2024-KON-001): ").strip(),
        'license_type': input("License Type (e.g., Restaurant): ").strip(),
        'owner_name': input("Owner Name: ").strip(),
        'citizen_id': input("TC ID: ").strip(),
        'region': input("Region (e.g., Selcuklu): ").strip(),
        'issue_date': input("Issue Date (YYYY-MM-DD): ").strip(),
        'expiry_date': input("Expiry Date (YYYY-MM-DD): ").strip(),
    }
    
    # Ask for PDF
    pdf_path = input("PDF Path (press Enter to skip): ").strip()
    
    if not pdf_path:
        pdf_path = None
    elif not Path(pdf_path).exists():
        print(f" ️  PDF file not found: {pdf_path}")
        pdf_path = None
    
    # Issue license
    try:
        result = issuer.issue_license(license_data, pdf_path)
        
        if result['success']:
            print(f"\n   License issued successfully!")
            print(f"  QR Code: {result['qr_url']}")
            if result.get('ipfs_hash'):
                print(f"  IPFS: {result['ipfs_hash']}")
            
            # Ask to view QR code
            view = input("\nOpen QR code image? (y/n): ").strip().lower()
            if view == 'y':
                import os
                qr_file = Path(f"data/qr_codes/{license_data['license_id']}.png")
                if qr_file.exists():
                    os.system(f"xdg-open {qr_file}")
    
    except Exception as e:
        print(f"\n   Error issuing license: {e}")
        import traceback
        traceback.print_exc()


def verify_license_interactive(issuer: LicenseIssuer):
    """Interactive license verification"""
    print(f"\n  VERIFY LICENSE")
    print("-" * 60)
    
    license_id = input("Enter License ID to verify: ").strip()
    
    # Get license info
    info = issuer.get_license_info(license_id)
    
    if info:
        print(f"\n   LICENSE FOUND")
        print(f"\n  License Information:")
        print(f"   License ID: {info.get('license_id')}")
        print(f"   Type: {info.get('license_type')}")
        print(f"   Owner: {info.get('owner_name')}")
        print(f"   TC ID: {info.get('citizen_id')}")
        print(f"   Region: {info.get('region')}")
        print(f"   Issue Date: {info.get('issue_date')}")
        print(f"   Expiry Date: {info.get('expiry_date')}")
        print(f"   Authority: {info.get('authority')}")
        
        if info.get('ipfs_hash'):
            print(f"\n  IPFS Hash: {info['ipfs_hash']}")
            print(f"   Gateway: https://ipfs.io/ipfs/{info['ipfs_hash']}")
            
            # Offer to download PDF
            download = input("\nDownload and decrypt PDF? (y/n): ").strip().lower()
            if download == 'y':
                from utils.ipfs_manager import IPFSManager
                ipfs = IPFSManager()
                
                output_file = Path(f"data/documents/{license_id}_decrypted.pdf")
                
                success = ipfs.download_and_decrypt(
                    info['ipfs_hash'],
                    license_id,
                    str(output_file)
                )
                
                if success:
                    print(f"   PDF downloaded: {output_file}")
                    
                    view = input("Open PDF? (y/n): ").strip().lower()
                    if view == 'y':
                        import os
                        os.system(f"xdg-open {output_file}")
    else:
        print(f"\n   License not found: {license_id}")


def main():
    """Main application loop"""
    print("\n  Starting Konya E-Ruhsat System...")
    
    # Initialize issuer
    try:
        issuer = LicenseIssuer()
    except Exception as e:
        print(f"   Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Main loop
    while True:
        print_menu()
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            issue_license_interactive(issuer)
        
        elif choice == '2':
            verify_license_interactive(issuer)
        
        elif choice == '3':
            license_id = input("Enter License ID: ").strip()
            info = issuer.get_license_info(license_id)
            if info:
                import json
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                print("   License not found")
        
        elif choice == '4':
            print("\n  Goodbye!")
            break
        
        else:
            print("   Invalid option")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()