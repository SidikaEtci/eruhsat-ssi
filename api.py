"""FastAPI Server with Robust Verification and Decryption"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import shutil
import os
import json
from services.issuer import LicenseIssuer
from services.verifier import LicenseVerifier
import config

app = FastAPI(title="Decentralized License System")
app.mount("/data", StaticFiles(directory="data"), name="data")

issuer = LicenseIssuer()
verifier = LicenseVerifier()

@app.post("/issue")
async def issue_license(
    license_id: str = Form(...),
    license_type: str = Form(...),
    owner_name: str = Form(...),
    citizen_id: str = Form(...),
    region: str = Form(...),
    issue_date: str = Form(...),
    expiry_date: str = Form(...),
    document: UploadFile = File(...)
):
    try:
        temp_path = f"data/documents/temp_{document.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(document.file, buffer)

        data = {
            "license_id": license_id,
            "license_type": license_type,
            "owner_name": owner_name,
            "citizen_id": citizen_id,
            "region": region,
            "issue_date": issue_date,
            "expiry_date": expiry_date
        }

        result = issuer.issue_license(data, pdf_path=temp_path)
        if os.path.exists(temp_path): os.remove(temp_path)

        return {"status": "success", "ipfs_hash": result['ipfs_hash'], "qr_url": result['qr_url']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify")
async def verify_license(payload: dict):
    """Safely verifies license with key checking"""
    try:
        # Check if 'data' key exists safely to avoid KeyError
        if 'data' not in payload:
            raise HTTPException(status_code=400, detail="Missing 'data' field in JSON")
            
        # 1. Digital Signature Check (Offline)
        # Using json.dumps to ensure data is stringified for verification
        is_valid = verifier.verify_offline(json.dumps(payload))
        
        # 2. Status Check (Online Simulation)
        license_id = payload['data'].get('id')
        info = issuer.get_license_info(license_id)
        
        status = "Active" if info and info.get('status') != 'revoked' else "Invalid or Revoked"
        
        return {
            "is_signature_valid": is_valid,
            "online_status": status,
            "license_data": payload['data']
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Verification Error: {str(e)}")

@app.get("/view-document/{license_id}")
async def view_document(license_id: str):
    """
    Downloads from IPFS, decrypts, and serves the original PDF
    """
    info = issuer.get_license_info(license_id)
    if not info or not info.get('ipfs_hash'):
        raise HTTPException(status_code=404, detail="License record not found")

    output_path = config.DOCUMENTS_DIR / f"{license_id}_decrypted.pdf"
    
    # Decrypt using the key derived from license_id
    success = verifier.ipfs.download_and_decrypt_document(
        info['ipfs_hash'], 
        license_id, 
        str(output_path)
    )
    
    if success:
        return FileResponse(output_path, media_type='application/pdf')
    raise HTTPException(status_code=500, detail="Decryption failed")

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()