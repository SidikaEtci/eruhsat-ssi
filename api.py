"""
FastAPI Backend for E-Ruhsat System
Konya Blockchain-Based Digital License Management
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import shutil
from datetime import datetime
import io

from services.issuer import LicenseIssuer
from utils.ipfs_manager import IPFSManager
from utils.auth import AuthManager
import config

# Initialize FastAPI app
app = FastAPI(
    title="Konya E-Ruhsat API",
    description="Blockchain-based digital license management system with Smart Contracts",
    version="2.0.0"
)

# CORS middleware
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
    auth_manager = AuthManager()
    print("\n✅ All services initialized successfully\n")
except Exception as e:
    print(f"\n⚠️  Warning during initialization: {e}\n")
    issuer = None
    ipfs = None
    auth_manager = None


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


@app.get("/login.html", response_class=HTMLResponse)
async def login_page():
    """Serve login page"""
    html_file = Path("web/login.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    raise HTTPException(status_code=404, detail="Login page not found")


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


@app.get("/verify-qr/{license_id}", response_class=HTMLResponse)
async def verify_qr_page(license_id: str):
    """Serve QR verification page"""
    html_file = Path("web/verify_qr.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    raise HTTPException(status_code=404, detail="Verification page not found")


@app.get("/qr-gallery", response_class=HTMLResponse)
async def qr_gallery():
    """QR Code gallery page"""
    html_file = Path("web/qr_gallery.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    raise HTTPException(status_code=404, detail="Gallery not found")

@app.get("/qr-reader", response_class=HTMLResponse)
async def qr_reader():
    """Offline QR code reader page"""
    html_file = Path("web/verify_qr_offline.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    raise HTTPException(status_code=404, detail="QR reader not found")
    
# ==================== AUTHENTICATION API ====================

@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """
    User login endpoint
    
    Returns session token if successful
    """
    result = auth_manager.login(username, password)
    
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Hatalı kullanıcı adı veya şifre"
        )
    
    return {
        "success": True,
        "token": result["token"],
        "user": {
            "username": result["username"],
            "role": result["role"],
            "name": result["name"]
        },
        "expires_at": result["expires_at"]
    }


@app.post("/api/logout")
async def logout(token: str = Form(...)):
    """User logout endpoint"""
    success = auth_manager.logout(token)
    
    return {
        "success": success,
        "message": "Çıkış yapıldı" if success else "Token bulunamadı"
    }


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
    
    Smart Contract validates business rules before issuance
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
        
        # Issue license (Smart Contract will validate)
        result = issuer.issue_license(license_data, str(pdf_path) if pdf_path else None)
        
        return {
            'success': True,
            'message': 'Ruhsat başarıyla verildi!',
            'data': result
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/verify/{license_id}")
async def verify_license(license_id: str):
    """
    Verify license by ID
    
    Uses Smart Contract verification
    """
    try:
        # Smart Contract verification
        contract_result = issuer.contract.verify_license(license_id)
        
        if contract_result["valid"]:
            # Get full info
            info = issuer.get_license_info(license_id)
            
            return {
                'success': True,
                'valid': True,
                'data': info,
                'message': contract_result["message"],
                'contract_status': contract_result["status"]
            }
        else:
            return {
                'success': True,
                'valid': False,
                'message': contract_result["message"],
                'contract_status': contract_result["status"]
            }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/licenses")
async def get_all_licenses():
    """Get all licenses from database"""
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
    """Get QR code image for a license"""
    qr_path = config.QR_CODES_DIR / f"{license_id}.png"
    
    if not qr_path.exists():
        raise HTTPException(status_code=404, detail="QR kodu bulunamadı")
    
    return FileResponse(qr_path, media_type="image/png")


# ==================== BLOCKCHAIN API ====================

@app.get("/api/blockchain")
async def get_blockchain():
    """Get blockchain ledger and statistics"""
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


@app.get("/api/contract/stats")
async def get_contract_stats():
    """Get smart contract statistics"""
    stats = issuer.contract.get_license_count()
    
    return {
        "success": True,
        "stats": stats
    }


# ==================== IPFS API ====================

@app.get("/api/ipfs-files")
async def get_ipfs_files():
    """Get all files stored on IPFS"""
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


# ==================== PDF DOWNLOAD & DECRYPTION ====================

@app.post("/api/download-pdf")
async def download_pdf_endpoint(
    license_id: str = Form(...),
    token: str = Form(...)
):
    """
    Download and decrypt PDF from IPFS
    
    Requires valid authentication token
    Only officers and admins can download
    """
    
    # Verify token
    user = auth_manager.verify_token(token)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Geçersiz veya süresi dolmuş token. Lütfen tekrar giriş yapın."
        )
    
    # Check role
    if user["role"] not in ["officer", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Bu işlem için zabıta veya admin yetkisi gereklidir"
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
        print(f"   User: {user['username']} ({user['role']})")
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
        
        print(f"✅ PDF successfully decrypted and sent to {user['username']}")
        
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
    """System health check"""
    return {
        'status': 'healthy',
        'services': {
            'issuer': issuer is not None,
            'ipfs': ipfs is not None,
            'auth': auth_manager is not None
        },
        'timestamp': datetime.now().isoformat()
    }
    
@app.get("/qr-reader", response_class=HTMLResponse)
async def qr_reader():
    """Offline QR code reader page"""
    html_file = Path("web/verify_qr_offline.html")
    if html_file.exists():
        return html_file.read_text(encoding='utf-8')
    raise HTTPException(status_code=404, detail="QR reader not found")

# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🚀 Starting Konya E-Ruhsat System v2.0")
    print("="*70)
    print("\n📍 Endpoints:")
    print("   • Main Page:         http://localhost:8000")
    print("   • Login:             http://localhost:8000/login.html")
    print("   • IPFS Explorer:     http://localhost:8000/ipfs_explorer.html")
    print("   • Blockchain:        http://localhost:8000/blockchain_explorer.html")
    print("   • QR Gallery:        http://localhost:8000/qr-gallery")
    print("   • API Docs:          http://localhost:8000/docs")
    print("\n👤 Default Users:")
    print("   • admin / admin123")
    print("   • zabita / zabita123")
    print("\n" + "="*70 + "\n")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )