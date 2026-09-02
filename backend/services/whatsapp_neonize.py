"""
WhatsApp transport built on neonize (Python bindings over the whatsmeow Go library).

Speaks the WhatsApp Web multi-device protocol directly over a WebSocket — there is
no browser, no DOM and no CSS selectors, so it does not break when WhatsApp changes
its UI. Same pairing model as WhatsApp Web: scan a QR from the phone once, the
session is then persisted in a local SQLite file.

Exposes the same four methods as WhatsAppService (the Playwright transport):
initialize(), check_status(), send_image(), close() — so main.py can swap between
them without any other change.

NOTE: this is the same unofficial protocol the Playwright transport rides on. It is
faster and far more stable, but it carries exactly the same account ban risk. Keep
sends slow and randomised.
"""

import asyncio
import os
import re
import traceback
from typing import Dict, Optional

import segno
from neonize.aioze.client import NewAClient
from neonize.events import ConnectedEv, DisconnectedEv, LoggedOutEv, PairStatusEv
from neonize.utils.jid import build_jid


class WhatsAppNeonizeService:
    """Automates WhatsApp via the multi-device protocol (no browser)."""

    def __init__(self, session_dir: str, output_dir: str = "outputs"):
        self.session_dir = os.path.abspath(session_dir)
        os.makedirs(self.session_dir, exist_ok=True)
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self._db_path = os.path.join(self.session_dir, "neonize.db")
        self._client: Optional[NewAClient] = None
        self._connect_task: Optional[asyncio.Task] = None

        self._logged_in = False
        self._qr_ready = False
        self._last_error: Optional[str] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def _qr_file(self) -> str:
        return os.path.join(self.output_dir, "wa_qr.png")

    async def initialize(self) -> Dict:
        """Connect to WhatsApp. Reuses the stored session; emits a QR if there is none."""
        try:
            if self._connect_task and not self._connect_task.done():
                if self._logged_in:
                    return {"success": True, "message": "Already connected ✓"}
                # Still unpaired: whatsmeow issues the pairing QR once and it has a
                # short life, so tear the connection down and start over to get a
                # fresh one. This is what the "Restart" button must do.
                await self.close()

            self._logged_in = False
            self._qr_ready = False
            self._last_error = None
            # Stale QR from a previous pairing would otherwise be shown as current.
            if os.path.exists(self._qr_file):
                os.remove(self._qr_file)

            # NewAClient's first argument is the SQLite session file path.
            self._client = NewAClient(self._db_path)

            @self._client.qr
            async def _on_qr(_client, data_qr: bytes):
                # Render the pairing QR to a PNG the frontend can display.
                segno.make_qr(data_qr).save(self._qr_file, scale=6, border=2)
                self._qr_ready = True

            @self._client.event(ConnectedEv)
            async def _on_connected(_client, _ev):
                self._logged_in = True
                self._qr_ready = False
                if os.path.exists(self._qr_file):
                    os.remove(self._qr_file)

            @self._client.event(PairStatusEv)
            async def _on_paired(_client, _ev):
                self._logged_in = True
                self._qr_ready = False

            @self._client.event(LoggedOutEv)
            async def _on_logged_out(_client, _ev):
                self._logged_in = False

            @self._client.event(DisconnectedEv)
            async def _on_disconnected(_client, _ev):
                self._logged_in = False

            # connect() runs the connection loop for as long as the session lives.
            self._connect_task = asyncio.create_task(self._run_connection())

            # Give the socket a moment to either restore the session or emit a QR,
            # so the first check_status() has something meaningful to report.
            for _ in range(30):
                if self._logged_in or self._qr_ready or self._last_error:
                    break
                await asyncio.sleep(0.25)

            if self._last_error:
                return {"success": False, "message": self._last_error}

            if self._logged_in:
                return {"success": True, "message": "Connected to WhatsApp ✓"}

            return {
                "success": True,
                "message": "Scan the QR code with WhatsApp on your phone (first run only).",
            }
        except Exception:
            self._last_error = traceback.format_exc()
            return {"success": False, "message": self._last_error}

    async def _run_connection(self):
        try:
            await self._client.connect()
        except asyncio.CancelledError:
            raise
        except Exception:
            self._last_error = traceback.format_exc()
            self._logged_in = False

    async def check_status(self) -> Dict:
        """Return logged-in status, a human-readable message, and a QR URL if pairing."""
        if not self._client or not self._connect_task:
            return {
                "logged_in": False,
                "message": "Not started. Click 'Initialize WhatsApp' first.",
            }

        if self._last_error:
            return {
                "logged_in": False,
                "message": f"Error: {self._last_error.strip().splitlines()[-1]}",
            }

        if self._logged_in:
            return {"logged_in": True, "message": "WhatsApp is connected ✓"}

        if self._qr_ready and os.path.exists(self._qr_file):
            return {
                "logged_in": False,
                "message": "Scan the QR code with WhatsApp on your phone.",
                # Cache-busted so a re-pairing QR replaces the previous image.
                "qr_url": f"/outputs/wa_qr.png?t={int(os.path.getmtime(self._qr_file))}",
            }

        return {"logged_in": False, "message": "Connecting to WhatsApp…"}

    async def close(self):
        if self._connect_task:
            self._connect_task.cancel()
            try:
                await self._connect_task
            except (asyncio.CancelledError, Exception):
                pass
            self._connect_task = None
        self._client = None
        self._logged_in = False
        self._qr_ready = False

    # ── Sending ───────────────────────────────────────────────────────────────

    async def send_image(self, phone: str, image_path: str, caption: str = "") -> bool:
        """Send an image to a phone number. Raises on any failure."""
        if not self._client or not self._logged_in:
            raise RuntimeError("WhatsApp not connected. Call initialize() first.")

        phone = self._normalize_phone(phone)
        abs_path = os.path.abspath(image_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Image not found: {abs_path}")

        # Verify the number is actually on WhatsApp before spending an upload on it.
        # The Playwright transport could only discover this from a popup after
        # navigating; here it is one cheap round trip.
        try:
            registered = await self._client.is_on_whatsapp(phone)
        except Exception:
            registered = None  # lookup failed — fall through and attempt the send

        if registered is not None:
            if not registered:
                raise ValueError(f"Phone number {phone} is not on WhatsApp.")
            if not registered[0].IsIn:
                raise ValueError(f"Phone number {phone} is not on WhatsApp.")

        with open(abs_path, "rb") as f:
            image_bytes = f.read()

        message = await self._client.build_image_message(
            image_bytes, caption=caption or None
        )
        response = await self._client.send_message(build_jid(phone), message)

        # A send that produced no server-assigned message ID did not reach WhatsApp.
        if not getattr(response, "ID", None):
            raise RuntimeError(f"WhatsApp did not acknowledge the message to {phone}.")

        return True

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Local number → international, without a leading +.

        DEFAULT_COUNTRY_CODE sets which country bare local numbers belong to
        (default 972 = Israel). Numbers that already carry a country code are
        passed through untouched, so a mixed-country contact list still works.
        """
        cc = os.getenv("DEFAULT_COUNTRY_CODE", "972").lstrip("+")
        digits = re.sub(r"\D", "", str(phone))

        # Already international for the configured country.
        if digits.startswith(cc) and len(digits) > len(cc):
            return digits
        # National format with a trunk 0 (e.g. IL 054-2160685).
        if digits.startswith("0"):
            return cc + digits[1:]
        # Bare subscriber number, no trunk 0 and no country code.
        if 8 <= len(digits) <= 10:
            return cc + digits
        return digits
