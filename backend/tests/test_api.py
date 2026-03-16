"""
API integration tests — Exercise every REST endpoint via HTTPX ASGI transport.
All tests run without a live server; no network or WhatsApp required.
"""
import io

import openpyxl
import pytest
from PIL import Image


# ── Health ────────────────────────────────────────────────────────────────────

async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


# ── Fonts ─────────────────────────────────────────────────────────────────────

async def test_get_fonts_returns_list(client):
    r = await client.get("/api/fonts")
    assert r.status_code == 200
    data = r.json()
    assert "fonts" in data
    assert isinstance(data["fonts"], list)


async def test_each_font_has_required_fields(client):
    r = await client.get("/api/fonts")
    for font in r.json()["fonts"]:
        assert "name"   in font
        assert "path"   in font
        assert "source" in font
        assert font["source"] in ("custom", "system")


# ── Excel Upload ──────────────────────────────────────────────────────────────

async def test_upload_valid_excel(client, sample_excel):
    with open(sample_excel, "rb") as f:
        r = await client.post(
            "/api/upload-excel",
            files={"file": ("contacts.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["total"] == 3
    contacts = data["contacts"]
    assert len(contacts) == 3
    # Names preserved
    names = [c["name"] for c in contacts]
    assert "ישראל ישראלי" in names
    assert "שרה כהן"     in names
    assert "דוד לוי"     in names


async def test_upload_excel_normalises_israeli_phones(client, sample_excel):
    with open(sample_excel, "rb") as f:
        r = await client.post(
            "/api/upload-excel",
            files={"file": ("contacts.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    contacts = r.json()["contacts"]
    # Local 05x numbers should be normalised to 9725x...
    for c in contacts:
        assert c["phone"].startswith("972"), f"Phone not normalised: {c['phone']}"


async def test_upload_wrong_extension_rejected(client):
    r = await client.post(
        "/api/upload-excel",
        files={"file": ("data.csv", b"name,phone\ntest,050", "text/csv")},
    )
    assert r.status_code == 400


async def test_upload_excel_with_duplicates(client, tmp_path):
    """Duplicate phone numbers should be reported as errors, not silently kept."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ישראל ישראלי", "0501234567"])
    ws.append(["כפיל ראשון",   "0501234567"])   # duplicate
    path = tmp_path / "dupes.xlsx"
    wb.save(str(path))

    with open(path, "rb") as f:
        r = await client.post(
            "/api/upload-excel",
            files={"file": ("dupes.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    data = r.json()
    assert data["total"] == 1                    # only first survives
    assert len(data["errors"]) >= 1              # duplicate error reported


async def test_upload_excel_skips_empty_rows(client, tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["שם א", "0501111111"])
    ws.append(["",     ""])          # empty row
    ws.append(["שם ב", "0502222222"])
    path = tmp_path / "gaps.xlsx"
    wb.save(str(path))

    with open(path, "rb") as f:
        r = await client.post(
            "/api/upload-excel",
            files={"file": ("gaps.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert r.json()["total"] == 2


# ── Image Upload ──────────────────────────────────────────────────────────────

async def _png_file_bytes(width=200, height=100):
    img = Image.new("RGB", (width, height), color=(40, 40, 120))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf.read(), width, height


async def test_upload_valid_image(client):
    data, w, h = await _png_file_bytes(300, 150)
    r = await client.post(
        "/api/upload-image",
        files={"file": ("card.png", data, "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["width"]  == 300
    assert body["height"] == 150
    assert body["url"].startswith("/outputs/")


async def test_upload_jpeg(client):
    img = Image.new("RGB", (100, 100), color=(200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    buf.seek(0)
    r = await client.post(
        "/api/upload-image",
        files={"file": ("photo.jpg", buf.read(), "image/jpeg")},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True


async def test_upload_non_image_rejected(client):
    r = await client.post(
        "/api/upload-image",
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert r.status_code == 400


# ── Preview Generation ────────────────────────────────────────────────────────

async def test_preview_returns_image_url(client, sample_image, default_text_config):
    r = await client.post("/api/preview", json={
        "image_path":  str(sample_image),
        "sample_name": "דוגמה",
        "text_config": default_text_config,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["previewUrl"].startswith("/outputs/")


async def test_preview_missing_image_returns_404(client, default_text_config):
    r = await client.post("/api/preview", json={
        "image_path":  "/nonexistent/path/image.png",
        "sample_name": "בדיקה",
        "text_config": default_text_config,
    })
    assert r.status_code == 404


async def test_preview_with_different_configs(client, sample_image):
    """Preview should succeed for different alignment and stroke values."""
    for align in ("left", "center", "right"):
        r = await client.post("/api/preview", json={
            "image_path":  str(sample_image),
            "sample_name": "שם",
            "text_config": {
                "font_name":    "Arial",
                "font_size":    48,
                "font_color":   "#FF0000",
                "x_percent":    0.3,
                "y_percent":    0.7,
                "align":        align,
                "stroke_width": 0,
                "stroke_color": "#000000",
            },
        })
        assert r.status_code == 200, f"Failed for align={align}"


# ── Process Status ────────────────────────────────────────────────────────────

async def test_process_status_idle(client):
    r = await client.get("/api/process/status")
    assert r.status_code == 200
    data = r.json()
    assert "isProcessing" in data
    assert "results"      in data
    assert "logs"         in data


async def test_stop_when_not_running(client):
    """Stop should succeed even if nothing is running."""
    r = await client.post("/api/process/stop")
    assert r.status_code == 200


# ── WhatsApp Status ───────────────────────────────────────────────────────────

async def test_whatsapp_status_before_init(client):
    """Before initialising the browser, status should report not logged in."""
    r = await client.get("/api/whatsapp/status")
    assert r.status_code == 200
    data = r.json()
    assert "logged_in" in data
    assert "message"   in data
    assert data["logged_in"] is False
