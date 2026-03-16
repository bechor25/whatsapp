"""
Shared pytest fixtures for backend tests.
"""
import io
import os
import sys

import pytest
from httpx import AsyncClient, ASGITransport

# Make sure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app  # noqa: E402


@pytest.fixture
async def client():
    """Async HTTPX client wired directly to the FastAPI app (no network needed)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_excel(tmp_path):
    """Create a minimal valid Excel file with 3 contacts."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["שם", "טלפון"])           # header
    ws.append(["ישראל ישראלי", "0501234567"])
    ws.append(["שרה כהן",     "0521234567"])
    ws.append(["דוד לוי",     "0541234567"])

    path = tmp_path / "contacts.xlsx"
    wb.save(str(path))
    return path


@pytest.fixture
def sample_image(tmp_path):
    """Create a minimal 400×200 white PNG template image."""
    from PIL import Image

    img = Image.new("RGB", (400, 200), color=(30, 30, 80))
    path = tmp_path / "template.png"
    img.save(str(path))
    return path


@pytest.fixture
def default_text_config():
    return {
        "font_name":    "Arial",
        "font_size":    60,
        "font_color":   "#FFFFFF",
        "x_percent":    0.5,
        "y_percent":    0.5,
        "align":        "center",
        "stroke_width": 2,
        "stroke_color": "#000000",
    }
