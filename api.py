"""
FastAPI Backend for E-Ruhsat System
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import shutil
import secrets
from datetime import datetime

from services.issuer import LicenseIssuer
from utils.ipfs_manager import IPFSManager
import config

app = FastAPI(title="Konya E-Ruhsat API")

# CORS - web arayüzü için
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
except Exception as e:
    print(f"⚠️  Warning: {e}")
    issuer = None
    ipfs = None


# ==========================================
# KULLANICI DOĞRULAMA (AUTHENTICATION) SİSTEMİ
# ==========================================
USERS = {
    "vatandas": {"password": "1234", "role": "citizen"},
    "zabita": {"password": "zabita123", "role": "officer"},
    "admin": {"password": "admin123", "role": "admin"}
}

security = HTTPBasic()

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Authenticate user"""
    username = credentials.username
    
    if username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    user = USERS[username]
    
    if not secrets.compare_digest(
        credentials.password.encode("utf8"),
        user["password"].encode("utf8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return {"username": username, "role": user["role"]}


# ==========================================
# API ENDPOINT'LERİ
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main page"""
    html_file = Path("web/index.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    return "<h1>E-Ruhsat System</h1><p>Web interface not found</p>"


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
    """Issue new license"""
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
        
        # Issue license
        result = issuer.issue_license(license_data, str(pdf_path) if pdf_path else None)
        
        return {
            'success': True,
            'message': 'Ruhsat başarıyla verildi!',
            'data': result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/verify/{license_id}")
async def verify_license(
    license_id: str,
    user: dict = Depends(get_current_user)  # ✅ Kimlik doğrulama gerekli
):
    """Verify license with role-based access"""
    try:
        info = issuer.get_license_info(license_id)
        
        if not info:
            return {
                'success': True,
                'valid': False,
                'message': 'Ruhsat bulunamadı'
            }
        
        # Role-based data filtering
        if user["role"] == "citizen":
            # Minimal data for citizens
            filtered_data = {
                'license_id': info.get('license_id'),
                'license_type': info.get('license_type'),
                'authority': info.get('authority'),
                'expiry_date': info.get('expiry_date'),
                'region': info.get('region')
                # NO: owner_name, citizen_id, ipfs_hash
            }
            return {
                'success': True,
                'valid': True,
                'role': 'citizen',
                'message': 'Ruhsat geçerli (sınırlı bilgi)',
                'data': filtered_data
            }
        
        elif user["role"] == "officer":
            # More data for officers
            filtered_data = {
                'license_id': info.get('license_id'),
                'license_type': info.get('license_type'),
                'owner_name': info.get('owner_name'),  # ✅ Can see
                'citizen_id': info.get('citizen_id'),  # ✅ Can see
                'authority': info.get('authority'),
                'expiry_date': info.get('expiry_date'),
                'region': info.get('region'),
                'ipfs_hash': info.get('ipfs_hash'),  # ✅ Can download
                'can_download_pdf': True
            }
            return {
                'success': True,
                'valid': True,
                'role': 'officer',
                'message': 'Ruhsat geçerli (yetkili erişim)',
                'data': filtered_data
            }
        
        else:  # admin
            # Full access
            return {
                'success': True,
                'valid': True,
                'role': 'admin',
                'message': 'Ruhsat geçerli (tam erişim)',
                'data': info
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download-pdf/{license_id}")
async def download_pdf(
    license_id: str,
    user: dict = Depends(get_current_user)
):
    """Download and decrypt PDF - ONLY for officers and admins"""
    
    # Check permission
    if user["role"] not in ["officer", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Bu işlem için yetkiniz yok (Sadece zabıta/admin)"
        )
    
    info = issuer.get_license_info(license_id)
    
    if not info or not info.get('ipfs_hash'):
        raise HTTPException(status_code=404, detail="Belge bulunamadı veya IPFS kaydı yok")
    
    # Download and decrypt
    output_file = config.DOCUMENTS_DIR / f"{license_id}_decrypted.pdf"
    
    success = ipfs.download_and_decrypt(
        info['ipfs_hash'],
        license_id,
        str(output_file)
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Belge indirilemedi veya şifresi çözülemedi")
    
    return FileResponse(
        output_file,
        media_type='application/pdf',
        filename=f"{license_id}.pdf"
    )


@app.get("/api/licenses")
async def get_all_licenses():
    """Get all licenses"""
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
    """Get QR code image"""
    qr_path = config.QR_CODES_DIR / f"{license_id}.png"
    
    if not qr_path.exists():
        raise HTTPException(status_code=404, detail="QR kodu bulunamadı")
    
    return FileResponse(qr_path)

@app.get("/api/blockchain")
async def get_blockchain():
    """Get blockchain ledger"""
    from utils.blockchain_logger import BlockchainLogger
    
    blockchain = BlockchainLogger()
    ledger = blockchain.get_ledger()
    stats = blockchain.get_stats()
    
    return {
        'ledger': ledger,
        'stats': stats
    }


@app.get("/api/ipfs-files")
async def get_ipfs_files():
    """Get all files on IPFS"""
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

# ==================== PDF DOWNLOAD SYSTEM ====================

from fastapi.responses import StreamingResponse
import io


@app.post("/api/download-pdf")
async def download_pdf_endpoint(
    license_id: str = Form(...),
    username: str = Form(None),
    password: str = Form(None)
):
    """
    Download and decrypt PDF from IPFS
    
    Access levels:
    - Citizen: Can download their own license
    - Officer: Can download any license
    - Admin: Can download any license
    """
    
    # Simple authentication (in production, use proper auth)
    USERS = {
        "vatandas": {"password": "1234", "role": "citizen"},
        "zabita": {"password": "zabita123", "role": "officer"},
        "admin": {"password": "admin123", "role": "admin"}
    }
    
    # Check credentials
    if username and password:
        if username not in USERS:
            raise HTTPException(status_code=401, detail="Geçersiz kullanıcı")
        
        if USERS[username]["password"] != password:
            raise HTTPException(status_code=401, detail="Hatalı şifre")
        
        user_role = USERS[username]["role"]
    else:
        # No auth provided
        user_role = None
    
    # Get license info
    info = issuer.get_license_info(license_id)
    
    if not info:
        raise HTTPException(status_code=404, detail="Ruhsat bulunamadı")
    
    if not info.get('ipfs_hash'):
        raise HTTPException(status_code=404, detail="Bu ruhsat için PDF belgesi yok")
    
    # Check permission
    if user_role not in ["officer", "admin"]:
        raise HTTPException(
            status_code=403, 
            detail="Bu işlem için yetkili (zabıta/admin) girişi gereklidir"
        )
    
    try:
        # Download and decrypt from IPFS
        output_file = config.DOCUMENTS_DIR / f"{license_id}_decrypted.pdf"
        
        success = ipfs.download_and_decrypt(
            info['ipfs_hash'],
            license_id,
            str(output_file)
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Belge indirilemedi")
        
        # Read file
        with open(output_file, 'rb') as f:
            pdf_data = f.read()
        
        # Clean up
        output_file.unlink()
        
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


@app.get("/api/preview-encrypted/{ipfs_hash}")
async def preview_encrypted_file(ipfs_hash: str):
    """
    Preview encrypted file info (without decrypting)
    Shows that file exists on IPFS
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
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)