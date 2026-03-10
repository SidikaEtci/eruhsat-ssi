"""
FastAPI Backend for E-Ruhsat System
Konya Blockchain-Based Digital License Management
"""
# --- PATH FIX İÇİN EKLENEN KISIM BAŞLANGICI ---
import sys
import os
# Betiğin bulunduğu dizini bul ve ana dizini (bir üst klasörü) Python yoluna ekle
current_dir = os.path.dirname(os.path.abspath(__file__))
# Eğer api.py ana dizindeyse burayı aktif et:
sys.path.append(current_dir) 
# Eğer api.py bir alt klasördeyse (örn: src/api.py), aşağıdaki satırı kullan:
# sys.path.append(os.path.dirname(current_dir))
# --- PATH FIX İÇİN EKLENEN KISIM BİTİŞİ ---

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import shutil
from datetime import datetime
import io

from services.issuer import LicenseIssuer
from utils.ipfs_manager import IPFSManager
import config

# Initialize FastAPI app
app = FastAPI(
    title="Konya E-Ruhsat API",
    description="Blockchain-based digital license management system",
    version="1.0.0"
)

# CORS middleware - allow web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/data", StaticFiles(directory="data"), name="data")

# Initialize services
try:
    issuer = LicenseIssuer()
    ipfs = IPFSManager()
    print("✅ All services initialized successfully")
except Exception as e:
    print(f"⚠️  Warning during initialization: {e}")
    issuer = None
    ipfs = None


# ==================== WEB PAGES ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main page"""
    html_file = Path("web/index.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    return HTMLResponse("""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>🏛️ Konya E-Ruhsat System</h1>
                <p>Web interface not found. Please check web/index.html</p>
            </body>
        </html>
    """)


@app.get("/ipfs_explorer.html", response_class=HTMLResponse)
async def ipfs_explorer():
    """Serve IPFS Explorer page"""
    html_file = Path("web/ipfs_explorer.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    raise HTTPException(status_code=404, detail="IPFS Explorer not found")


@app.get("/blockchain_explorer.html", response_class=HTMLResponse)
async def blockchain_explorer():
    """Serve Blockchain Explorer page"""
    html_file = Path("web/blockchain_explorer.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    raise HTTPException(status_code=404, detail="Blockchain Explorer not found")

@app.get("/blockchain_detailed.html", response_class=HTMLResponse)
async def blockchain_detailed():
    """Serve Detailed Blockchain Explorer page"""
    html_file = Path("web/blockchain_detailed.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    raise HTTPException(status_code=404, detail="Blockchain Detailed Explorer not found")
    
# ==================== LICENSE MANAGEMENT API ====================

@app.post("/api/issue")
async def issue_license(
    license_id: str = Form(...),
    license_type: str = Form(...),
    owner_name: str = Form(...),
    citizen_id: str = Form(...),
    region: str = Form(...),
    issue_date: str = Form(...),
    expiry_date: str = Form(...),
    pdf_file: UploadFile = File(None)
):
    """
    Issue new digital license
    
    Args:
        license_id: Unique license identifier
        license_type: Type of license
        owner_name: License owner's name
        citizen_id: TC identification number
        region: District/region
        issue_date: Issue date (YYYY-MM-DD)
        expiry_date: Expiry date (YYYY-MM-DD)
        pdf_file: Optional PDF document
        
    Returns:
        Success status, IPFS hash, and QR code URL
    """
    try:
        # Prepare license data
        license_data = {
            'license_id': license_id,
            'license_type': license_type,
            'owner_name': owner_name,
            'citizen_id': citizen_id,
            'region': region,
            'issue_date': issue_date,
            'expiry_date': expiry_date,
        }
        
        # Save PDF if provided
        pdf_path = None
        if pdf_file and pdf_file.filename:
            pdf_path = config.DOCUMENTS_DIR / f"{license_id}.pdf"
            with open(pdf_path, 'wb') as f:
                shutil.copyfileobj(pdf_file.file, f)
            print(f"📄 PDF saved: {pdf_path}")
        
        # Issue license
        result = issuer.issue_license(license_data, str(pdf_path) if pdf_path else None)
        
        return {
            'success': True,
            'message': 'Ruhsat başarıyla verildi!',
            'data': result
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/verify/{license_id}")
async def verify_license(license_id: str):
    """
    Verify license by ID
    
    Args:
        license_id: License identifier to verify
        
    Returns:
        Validation status and license information
    """
    try:
        info = issuer.get_license_info(license_id)
        
        if info:
            return {
                'success': True,
                'valid': True,
                'data': info,
                'message': 'Ruhsat geçerli'
            }
        else:
            return {
                'success': True,
                'valid': False,
                'message': 'Ruhsat bulunamadı'
            }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/licenses")
async def get_all_licenses():
    """
    Get all licenses from database
    
    Returns:
        List of all licenses
    """
    try:
        db_path = config.DATA_DIR / "credentials.json"
        
        if not db_path.exists():
            return {'licenses': []}
        
        with open(db_path, 'r', encoding='utf-8') as f:
            licenses = json.load(f)
        
        return {'licenses': licenses}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/qr/{license_id}")
async def get_qr_code(license_id: str):
    """
    Get QR code image for a license
    
    Args:
        license_id: License identifier
        
    Returns:
        QR code PNG image
    """
    qr_path = config.QR_CODES_DIR / f"{license_id}.png"
    
    if not qr_path.exists():
        raise HTTPException(status_code=404, detail="QR kodu bulunamadı")
    
    return FileResponse(qr_path, media_type="image/png")


# ==================== BLOCKCHAIN API ====================

@app.get("/api/blockchain")
async def get_blockchain():
    """
    Get blockchain ledger and statistics
    
    Returns:
        Complete blockchain ledger with stats
    """
    from utils.blockchain_logger import BlockchainLogger
    
    try:
        blockchain = BlockchainLogger()
        ledger = blockchain.get_ledger()
        stats = blockchain.get_stats()
        
        return {
            'ledger': ledger,
            'stats': stats
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== IPFS API ====================

@app.get("/api/ipfs-files")
async def get_ipfs_files():
    """
    Get all files stored on IPFS
    
    Returns:
        List of files with IPFS hashes
    """
    try:
        db_path = config.DATA_DIR / "credentials.json"
        
        if not db_path.exists():
            return {'files': []}
        
        with open(db_path, 'r', encoding='utf-8') as f:
            licenses = json.load(f)
        
        files = []
        for lic in licenses:
            if lic.get('ipfs_hash'):
                files.append({
                    'license_id': lic['license_id'],
                    'license_type': lic['license_type'],
                    'ipfs_hash': lic['ipfs_hash'],
                    'document_hash': lic.get('document_hash', ''),
                    'created_at': lic.get('created_at', '')
                })
        
        return {'files': files}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/preview-encrypted/{ipfs_hash}")
async def preview_encrypted_file(ipfs_hash: str):
    """
    Preview encrypted file info (without decrypting)
    
    Args:
        ipfs_hash: IPFS content hash
        
    Returns:
        File existence status and metadata
    """
    try:
        # Verify file exists on IPFS
        exists = ipfs.verify_file_exists(ipfs_hash)
        
        if exists:
            return {
                'success': True,
                'message': 'Şifreli belge IPFS\'te mevcut',
                'ipfs_hash': ipfs_hash,
                'gateway_url': f'https://ipfs.io/ipfs/{ipfs_hash}',
                'note': 'Bu belge AES-256 ile şifrelenmiştir'
            }
        else:
            return {
                'success': False,
                'message': 'Belge IPFS\'te bulunamadı'
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PDF DOWNLOAD & DECRYPTION ====================

@app.post("/api/download-pdf")
async def download_pdf_endpoint(
    license_id: str = Form(...),
    username: str = Form(None),
    password: str = Form(None)
):
    """
    Download and decrypt PDF from IPFS
    
    Access levels:
    - Officer (zabita): Can download any license
    - Admin: Can download any license
    
    Args:
        license_id: License identifier
        username: User's username
        password: User's password
        
    Returns:
        Decrypted PDF file
    """
    
    # Simple authentication (in production, use proper auth system)
    USERS = {
        "vatandas": {"password": "1234", "role": "citizen"},
        "zabita": {"password": "zabita123", "role": "officer"},
        "admin": {"password": "admin123", "role": "admin"}
    }
    
    # Check credentials
    if username and password:
        if username not in USERS:
            raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı")
        
        if USERS[username]["password"] != password:
            raise HTTPException(status_code=401, detail="Hatalı şifre")
        
        user_role = USERS[username]["role"]
    else:
        raise HTTPException(status_code=401, detail="Kimlik doğrulama gerekli")
    
    # Check permission
    if user_role not in ["officer", "admin"]:
        raise HTTPException(
            status_code=403, 
            detail="Bu işlem için yetkili (zabıta/admin) girişi gereklidir"
        )
    
    # Get license info
    info = issuer.get_license_info(license_id)
    
    if not info:
        raise HTTPException(status_code=404, detail="Ruhsat bulunamadı")
    
    if not info.get('ipfs_hash'):
        raise HTTPException(status_code=404, detail="Bu ruhsat için PDF belgesi yok")
    
    try:
        # Download and decrypt from IPFS
        output_file = config.DOCUMENTS_DIR / f"{license_id}_decrypted.pdf"
        
        print(f"\n📥 Downloading PDF for {license_id}...")
        print(f"   User: {username} ({user_role})")
        print(f"   IPFS Hash: {info['ipfs_hash']}")
        
        success = ipfs.download_and_decrypt(
            info['ipfs_hash'],
            license_id,
            str(output_file)
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Belge indirilemedi veya şifresi çözülemedi")
        
        # Read file
        with open(output_file, 'rb') as f:
            pdf_data = f.read()
        
        # Clean up
        output_file.unlink()
        
        print(f"✅ PDF successfully decrypted and sent to user")
        
        # Return as downloadable file
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{license_id}.pdf"'
            }
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"İndirme hatası: {str(e)}")


# ==================== HEALTH CHECK ====================

@app.get("/api/health")
async def health_check():
    """
    System health check
    
    Returns:
        Service status information
    """
    return {
        'status': 'healthy',
        'services': {
            'issuer': issuer is not None,
            'ipfs': ipfs is not None
        },
        'timestamp': datetime.now().isoformat()
    }


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 Starting Konya E-Ruhsat System")
    print("="*60)
    print("\n📍 Endpoints:")
    print("   • Main Page:        http://localhost:8000")
    print("   • IPFS Explorer:    http://localhost:8000/ipfs_explorer.html")
    print("   • Blockchain:       http://localhost:8000/blockchain_explorer.html")
    print("   • API Docs:         http://localhost:8000/docs")
    print("\n" + "="*60 + "\n")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )