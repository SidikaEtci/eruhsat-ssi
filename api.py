"""
FastAPI backend for the Turkey municipal e-license platform.
"""
from datetime import datetime
from pathlib import Path
import io
import json
import shutil

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from services.issuer import LicenseIssuer
from utils.auth import AuthManager
from utils.ipfs_manager import IPFSManager
import config

WEB_DIR = Path("web")

app = FastAPI(
    title="Turkey E-License API",
    description="Blockchain-based digital license management for Turkish municipalities",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/data", StaticFiles(directory="data"), name="data")

try:
    issuer = LicenseIssuer()
    ipfs = IPFSManager()
    auth_manager = AuthManager()
    print("\n   All services initialized successfully\n")
except Exception as exc:
    print(f"\n   Warning during initialization: {exc}\n")
    issuer = None
    ipfs = None
    auth_manager = None


def _serve_html(filename: str) -> HTMLResponse:
    html_path = WEB_DIR / filename
    if not html_path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


def _license_public_view(license_info: dict) -> dict:
    return {
        "license_id": license_info.get("license_id"),
        "license_type": license_info.get("license_type"),
        "city_name": license_info.get("city_name"),
        "city_slug": license_info.get("city_slug"),
        "owner_name": license_info.get("owner_name"),
        "business_name": license_info.get("business_name"),
        "address": license_info.get("address"),
        "region": license_info.get("region"),
        "valid_from": license_info.get("issue_date"),
        "valid_until": license_info.get("expiry_date"),
        "authority": license_info.get("authority"),
    }


def _parse_expiry_date(expiry_date_str: str) -> datetime | None:
    try:
        if "T" in expiry_date_str or "Z" in expiry_date_str:
            return datetime.fromisoformat(expiry_date_str.replace("Z", "+00:00"))
        return datetime.strptime(expiry_date_str, "%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(expiry_date_str[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _build_verify_response(license_info: dict) -> dict:
    if license_info.get("revoked", False):
        return {
            "valid": False,
            "reason": "revoked",
            "message": "License has been revoked",
            "license": _license_public_view(license_info),
        }

    expiry_date_str = license_info.get("expiry_date")
    issue_date_str = license_info.get("issue_date")
    license_view = _license_public_view(license_info)

    if not expiry_date_str:
        return {
            "valid": True,
            "message": "License is valid (no expiry date on record)",
            "license": license_view,
        }

    expiry_date = _parse_expiry_date(expiry_date_str)
    if expiry_date is None:
        return {
            "valid": True,
            "message": "License is valid (expiry date could not be parsed)",
            "license": license_view,
        }

    now = datetime.now(expiry_date.tzinfo) if expiry_date.tzinfo else datetime.now()
    if now > expiry_date:
        return {
            "valid": False,
            "reason": "expired",
            "message": "License has expired",
            "license": license_view,
        }

    return {
        "valid": True,
        "message": "License is valid",
        "license": license_view,
    }


# ==================== WEB PAGES ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = WEB_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;text-align:center;padding:50px'>"
        "<h1>Turkey E-License Platform</h1>"
        "<p>Web interface not found. Check web/index.html</p>"
        "</body></html>"
    )


@app.get("/login.html", response_class=HTMLResponse)
async def login_page():
    return _serve_html("login.html")


@app.get("/ipfs_explorer.html", response_class=HTMLResponse)
async def ipfs_explorer():
    return _serve_html("ipfs_explorer.html")


@app.get("/blockchain_explorer.html", response_class=HTMLResponse)
async def blockchain_explorer():
    return _serve_html("blockchain_explorer.html")


@app.get("/blockchain_detailed.html", response_class=HTMLResponse)
async def blockchain_detailed():
    return _serve_html("blockchain_detailed.html")


@app.get("/verify-qr/{license_id}", response_class=HTMLResponse)
async def verify_qr_page(license_id: str):
    return _serve_html("verify_qr.html")


@app.get("/qr-gallery", response_class=HTMLResponse)
async def qr_gallery():
    return _serve_html("qr_gallery.html")


@app.get("/qr-reader", response_class=HTMLResponse)
async def qr_reader():
    return _serve_html("verify_qr_offline.html")


# ==================== SETTINGS API ====================

@app.get("/api/settings")
async def get_settings(city: str | None = Query(None)):
    """Public settings for UI branding and city/district lists."""
    return config.settings_payload(city)


@app.get("/web/city-settings.js", response_class=HTMLResponse)
async def city_settings_js():
    """Shared client script for municipality selection."""
    script_path = WEB_DIR / "city-settings.js"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="city-settings.js not found")
    return HTMLResponse(
        script_path.read_text(encoding="utf-8"),
        media_type="application/javascript",
    )


# ==================== AUTHENTICATION API ====================

@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    result = auth_manager.login(username, password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "success": True,
        "token": result["token"],
        "user": {
            "username": result["username"],
            "role": result["role"],
            "name": result["name"],
        },
        "expires_at": result["expires_at"],
    }


@app.post("/api/logout")
async def logout(token: str = Form(...)):
    success = auth_manager.logout(token)
    return {
        "success": success,
        "message": "Logged out" if success else "Token not found",
    }


# ==================== LICENSE MANAGEMENT API ====================

@app.post("/api/issue")
async def issue_license(
    license_id: str = Form(...),
    license_type: str = Form(...),
    owner_name: str = Form(...),
    business_name: str = Form(...),
    address: str = Form(...),
    citizen_id: str = Form(...),
    region: str = Form(...),
    issue_date: str = Form(...),
    expiry_date: str = Form(...),
    city_slug: str = Form(None),
    pdf_file: UploadFile = File(None),
):
    try:
        slug = config.resolve_city_slug(city_slug=city_slug)
        paths = config.paths_for_city(slug)

        license_data = {
            "license_id": license_id,
            "license_type": license_type,
            "owner_name": owner_name,
            "business_name": business_name,
            "address": address,
            "citizen_id": citizen_id,
            "region": region,
            "issue_date": issue_date,
            "expiry_date": expiry_date,
        }

        pdf_path = None
        if pdf_file and pdf_file.filename:
            pdf_path = paths["documents_dir"] / f"{license_id}.pdf"
            with open(pdf_path, "wb") as file:
                shutil.copyfileobj(pdf_file.file, file)

        result = issuer.issue_license(
            license_data,
            str(pdf_path) if pdf_path else None,
            city_slug=slug,
        )
        return {
            "success": True,
            "message": "License issued successfully",
            "data": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/verify/{license_id}")
async def verify_license(license_id: str):
    try:
        license_info = issuer.get_license_info(license_id)
        if not license_info:
            return {
                "valid": False,
                "reason": "not_found",
                "message": "License not found",
            }
        return _build_verify_response(license_info)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/licenses")
async def get_all_licenses(city: str | None = Query(None)):
    return {"licenses": issuer.list_licenses(city_slug=city)}


@app.get("/api/qr/{license_id}")
async def get_qr_code(license_id: str, city: str | None = Query(None)):
    slug = config.resolve_city_slug(license_id=license_id, city_slug=city)
    qr_path = config.paths_for_city(slug)["qr_codes_dir"] / f"{license_id}.png"
    if not qr_path.exists():
        raise HTTPException(status_code=404, detail="QR code not found")
    return FileResponse(qr_path, media_type="image/png")


# ==================== BLOCKCHAIN API ====================

@app.get("/api/blockchain")
async def get_blockchain(city: str | None = Query(None)):
    from utils.blockchain_logger import BlockchainLogger

    slug = config.resolve_city_slug(city_slug=city)
    blockchain = BlockchainLogger(slug)
    return {
        "city_slug": slug,
        "ledger": blockchain.get_ledger(),
        "stats": blockchain.get_stats(),
    }


@app.get("/api/indy/stats")
async def get_indy_stats(city: str | None = Query(None)):
    """Get Hyperledger Indy ledger statistics."""
    from utils.indy_ledger import IndyLedgerManager

    slug = config.resolve_city_slug(city_slug=city)
    try:
        indy_manager = IndyLedgerManager(slug)
        stats = indy_manager.get_ledger_stats()
        return {
            "success": True,
            "city_slug": slug,
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/indy/verify/{license_id}")
async def verify_credential_on_indy(license_id: str, city: str | None = Query(None)):
    """Verify a credential on Hyperledger Indy ledger."""
    from utils.indy_ledger import IndyLedgerManager, run_async

    slug = config.resolve_city_slug(license_id=license_id, city_slug=city)
    try:
        indy_manager = IndyLedgerManager(slug)
        result = run_async(indy_manager.verify_credential_on_ledger(license_id))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/indy/revoke/{license_id}")
async def revoke_credential_on_indy(
    license_id: str,
    reason: str = Form(...),
    city: str | None = Query(None),
):
    """Revoke a credential on Hyperledger Indy ledger."""
    from utils.indy_ledger import IndyLedgerManager, run_async

    slug = config.resolve_city_slug(license_id=license_id, city_slug=city)
    try:
        indy_manager = IndyLedgerManager(slug)
        result = run_async(indy_manager.revoke_credential(license_id, reason))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/contract/stats")
async def get_contract_stats(city: str | None = Query(None)):
    slug = config.resolve_city_slug(city_slug=city)
    return {
        "success": True,
        "city_slug": slug,
        "stats": issuer.contract_stats(slug),
    }


# ==================== IPFS API ====================

@app.get("/api/ipfs-files")
async def get_ipfs_files(city: str | None = Query(None)):
    licenses = issuer.list_licenses(city_slug=city)
    files = [
        {
            "license_id": lic["license_id"],
            "license_type": lic["license_type"],
            "city_slug": lic.get("city_slug"),
            "city_name": lic.get("city_name"),
            "ipfs_hash": lic["ipfs_hash"],
            "document_hash": lic.get("document_hash", ""),
            "created_at": lic.get("created_at", ""),
        }
        for lic in licenses
        if lic.get("ipfs_hash")
    ]
    return {"files": files}


# ==================== PDF DOWNLOAD ====================

@app.post("/api/download-pdf")
async def download_pdf_endpoint(license_id: str = Form(...), token: str = Form(...)):
    user = auth_manager.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please sign in again.",
        )

    if user["role"] not in ("officer", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Officer or admin privileges are required for this action",
        )

    info = issuer.get_license_info(license_id)
    if not info:
        raise HTTPException(status_code=404, detail="License not found")
    if not info.get("ipfs_hash"):
        raise HTTPException(status_code=404, detail="No PDF document for this license")

    slug = config.resolve_city_slug(license_id=license_id)
    paths = config.paths_for_city(slug)
    output_file = paths["documents_dir"] / f"{license_id}_decrypted.pdf"
    try:
        success = ipfs.download_and_decrypt(
            info["ipfs_hash"],
            license_id,
            str(output_file),
        )
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Could not download or decrypt the document",
            )

        with open(output_file, "rb") as file:
            pdf_data = file.read()
        output_file.unlink(missing_ok=True)

        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{license_id}.pdf"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Download failed: {exc}") from exc


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "issuer": issuer is not None,
            "ipfs": ipfs is not None,
            "auth": auth_manager is not None,
        },
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 70)
    print(f"  Starting Turkey E-License Platform v3.0 ({config.CITY_NAME})")
    print("=" * 70)
    print("\n  Endpoints:")
    print("   • Main Page:        http://localhost:8000")
    print("   • Login:            http://localhost:8000/login.html")
    print("   • IPFS Explorer:    http://localhost:8000/ipfs_explorer.html")
    print("   • Blockchain:       http://localhost:8000/blockchain_explorer.html")
    print("   • QR Gallery:       http://localhost:8000/qr-gallery")
    print("   • API Docs:         http://localhost:8000/docs")
    print(f"\n  Default city: {config.CITY_SLUG} (set CITY_SLUG to change)")
    print("\n  Default users:")
    print("   • admin / admin123")
    print("   • zabita / zabita123")
    print("\n" + "=" * 70 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
