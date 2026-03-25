import asyncio
import os
import re
import traceback
from typing import Dict, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)


class WhatsAppService:
    """
    Automates WhatsApp Web via Playwright.
    Uses a *persistent* browser context so the QR scan is performed only once.
    """

    def __init__(self, session_dir: str):
        self.session_dir = os.path.abspath(session_dir)
        os.makedirs(self.session_dir, exist_ok=True)
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialize(self) -> Dict:
        """Launch a visible Chromium window pointing at WhatsApp Web."""
        try:
            if self._playwright is None:
                self._playwright = await async_playwright().start()

            # Close stale context if any
            if self._context:
                await self._context.close()
                self._context = None

            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=self.session_dir,
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 800},
            )

            pages = self._context.pages
            self._page = pages[0] if pages else await self._context.new_page()

            # If the window is closed by the user, reopen it automatically
            self._page.on("close", self._on_page_closed)

            await self._page.goto(
                "https://web.whatsapp.com", wait_until="domcontentloaded", timeout=30000
            )

            return {
                "success": True,
                "message": "Browser launched. Please scan the QR code shown in the browser window (first run only).",
            }
        except Exception as exc:
            msg = traceback.format_exc()
            return {"success": False, "message": msg}

    async def check_status(self) -> Dict:
        """Return logged-in status and a human-readable message."""
        if not self._page:
            return {
                "logged_in": False,
                "message": "Browser not started. Click 'Initialize WhatsApp' first.",
            }

        try:
            # QR code = not logged in yet
            qr = await self._page.locator('div[data-testid="qrcode"]').is_visible()
            if qr:
                return {
                    "logged_in": False,
                    "message": "Waiting for QR scan… open the browser and scan with WhatsApp.",
                }

            # Loading overlay
            loading = await self._page.locator('[data-testid="startup"]').is_visible()
            if loading:
                return {"logged_in": False, "message": "WhatsApp Web is loading…"}

            # Various selectors that indicate the main UI is ready
            ready_selectors = [
                'div[data-testid="chat-list"]',
                "#pane-side",
                'div[aria-label="Chat list"]',
            ]
            for sel in ready_selectors:
                try:
                    if await self._page.locator(sel).first.is_visible():
                        return {"logged_in": True, "message": "WhatsApp Web is ready ✓"}
                except Exception:
                    pass

            return {"logged_in": False, "message": "Waiting for WhatsApp Web to load…"}

        except Exception as exc:
            return {"logged_in": False, "message": f"Error: {exc}"}

    async def close(self):
        if self._context:
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None

    def _on_page_closed(self, page):
        """Called when the user closes the browser window.
        We null out _page so that check_status + send_image will
        reopen it automatically via initialize() next time."""
        self._page = None

    # ── Sending ───────────────────────────────────────────────────────────────

    async def send_image(self, phone: str, image_path: str, caption: str = "") -> bool:
        """Navigate to a WhatsApp chat and send an image."""
        if not self._page:
            raise RuntimeError("WhatsApp not initialized. Call initialize() first.")

        phone = self._normalize_phone(phone)
        abs_path = os.path.abspath(image_path)

        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Image not found: {abs_path}")

        # Open direct chat via URL
        await self._page.goto(
            f"https://web.whatsapp.com/send?phone={phone}",
            wait_until="domcontentloaded",
            timeout=30000,
        )

        # Wait for the message compose box
        # WhatsApp Web 2026: no data-testid; detect by contenteditable or any input area.
        compose_selectors = (
            'div[contenteditable="true"][data-tab="10"], '
            'div[contenteditable="true"][data-tab="6"], '
            'div[contenteditable="true"][aria-placeholder], '
            'footer div[contenteditable="true"], '
            'div[data-testid="conversation-compose-box-input"]'
        )
        try:
            await self._page.wait_for_selector(compose_selectors, timeout=30000)
        except Exception:
            # Detect invalid number popup (new UI uses a generic div/dialog)
            any_popup = await self._page.locator(
                'div[data-testid="popup-contents"], div[role="dialog"]'
            ).first.is_visible()
            if any_popup:
                raise ValueError(
                    f"Phone number {phone} is not on WhatsApp or is invalid."
                )
            raise TimeoutError(
                f"Timed out loading chat for {phone}. Verify the number."
            )

        await asyncio.sleep(1.5)  # let UI fully settle

        # ── Attach image ──────────────────────────────────────────────────────
        # CRITICAL: always go through the "+" menu → "תמונות וסרטונים".
        # WhatsApp Web uses a SINGLE hidden input[type=file] for ALL attachment
        # types (photos, stickers, documents). The type is determined by which
        # menu item was clicked to trigger the file chooser.
        # Calling set_input_files directly (without a prior menu click) causes
        # WhatsApp to send the file as a STICKER instead of a photo.
        file_set = False

        attach_btn_selectors = [
            '[data-icon="plus-rounded"]',
            '[data-icon="attach-menu-plus"]',
            '[data-icon="clip"]',
            '[data-icon="attach"]',
            'button[aria-label="צרף"]',
            'button[aria-label="Attach"]',
            'button[data-testid="compose-btn-attachment"]',
            'span[data-testid="attach-btn"]',
        ]
        # DOM-verified (2026-03) aria-label of the "Photos & Videos" menu item.
        # Must come first — other selectors are legacy / English fallbacks.
        photos_menu_selectors = [
            '[aria-label="תמונות וסרטונים"]',   # Hebrew 2026
            '[aria-label="תמונות וסרטוני וידאו"]',
            '[aria-label="Photos & videos"]',
            '[aria-label="Photos, GIF, Videos"]',
            'li[data-testid="mi-attach-image"]',
            '[data-icon="image"]',
        ]

        # Strategy 1: open the "+" menu first, THEN intercept the file-chooser
        # triggered specifically by the Photos menu item.
        # Splitting the steps (open menu → wait → start chooser listener → click
        # Photos) avoids a race where the listener starts too late.
        try:
            # Step A: open the attach dropdown
            opened = await self._click_first_visible(attach_btn_selectors)
            if not opened:
                raise RuntimeError("Could not open attach menu")
            await asyncio.sleep(0.7)  # wait for the menu to render

            # Step B: intercept the file-chooser opened by the Photos item
            async with self._page.expect_file_chooser(timeout=6000) as fc_info:
                clicked = await self._click_first_visible(photos_menu_selectors)
                if not clicked:
                    raise RuntimeError("Photos menu item not found")
            file_chooser = await fc_info.value
            await file_chooser.set_files(abs_path)
            file_set = True
        except Exception:
            pass

        if not file_set:
            # Strategy 2: same flow, but dismiss and retry once in case the
            # menu closed on its own or the first attempt left stale state.
            try:
                await self._page.keyboard.press("Escape")
                await asyncio.sleep(0.4)
                opened = await self._click_first_visible(attach_btn_selectors)
                if not opened:
                    raise RuntimeError("Could not open attach menu (retry)")
                await asyncio.sleep(0.7)
                async with self._page.expect_file_chooser(timeout=6000) as fc_info:
                    await self._click_first_visible(photos_menu_selectors)
                file_chooser = await fc_info.value
                await file_chooser.set_files(abs_path)
                file_set = True
            except Exception:
                pass

        if not file_set:
            try:
                ss_path = os.path.join(os.path.dirname(self.session_dir), "outputs", "wa_debug.png")
                await self._page.screenshot(path=ss_path)
            except Exception:
                pass
            raise RuntimeError("Could not attach image file. Screenshot saved to outputs/wa_debug.png")

        # ── Wait for the media preview to actually open ───────────────────────
        # STRICT selector: requires BOTH aria-label="שליחה" AND the send icon as a
        # direct descendant (:has). This avoids false-matching the "עדכן את WhatsApp"
        # update notification or any other element that only partially matches.
        MEDIA_PREVIEW_SEND_SEL = '[aria-label="שליחה"]:has([data-icon="wds-ic-send-filled"])'
        try:
            await self._page.wait_for_selector(
                MEDIA_PREVIEW_SEND_SEL, state="visible", timeout=15000
            )
        except Exception:
            try:
                ss_dir = os.path.join(os.path.dirname(self.session_dir), "outputs")
                await self._page.screenshot(path=os.path.join(ss_dir, "wa_nopreview.png"))
            except Exception:
                pass
            raise RuntimeError(
                f"Media preview did not open for {phone}. "
                "The image was not attached (screenshot saved to outputs/wa_nopreview.png)."
            )

        # ── Debug: dump send-screen DOM ───────────────────────────────────────
        try:
            ss_dir = os.path.join(os.path.dirname(self.session_dir), "outputs")
            await self._page.screenshot(path=os.path.join(ss_dir, "wa_media_preview.png"))
            media_elements = await self._page.evaluate('''() => {
                const res = [];
                document.querySelectorAll("button,[role=button],div[aria-label],span[aria-label]").forEach(el => {
                    const aria = el.getAttribute("aria-label");
                    const testid = el.getAttribute("data-testid");
                    const icon = el.querySelector("[data-icon]")?.getAttribute("data-icon");
                    if (aria || testid || icon)
                        res.push({tag: el.tagName, aria, testid, icon, text: el.innerText?.trim().slice(0,30)});
                });
                return res;
            }''')
            import json as _json
            with open(os.path.join(ss_dir, "wa_media_dom.json"), "w", encoding="utf-8") as f:
                _json.dump(media_elements, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # ── Optional caption ──────────────────────────────────────────────────
        if caption:
            for sel in [
                'div[data-testid="media-caption-input-container"] div[contenteditable="true"]',
                'div[contenteditable="true"][data-tab="7"]',
            ]:
                try:
                    el = self._page.locator(sel).first
                    if await el.is_visible():
                        await el.click()
                        await el.type(caption)
                        break
                except Exception:
                    pass

        # ── Send ──────────────────────────────────────────────────────────────
        # Use JavaScript to click the element that has BOTH aria-label="שליחה"
        # AND the wds-ic-send-filled icon inside it. This is the strictest possible
        # identifier and cannot be confused with the update-notification button.
        sent = await self._page.evaluate("""
() => {
    // Primary: שליחה element that contains the specific media-preview send icon
    for (const el of document.querySelectorAll('[aria-label="\u05e9\u05dc\u05d9\u05d7\u05d4"]')) {
        if (!el.querySelector('[data-icon="wds-ic-send-filled"]')) continue;
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0 && el.offsetParent !== null) {
            el.click();
            return true;
        }
    }
    // Fallback: climb up from the icon itself
    for (const icon of document.querySelectorAll('[data-icon="wds-ic-send-filled"]')) {
        const t = icon.closest('[aria-label]') ||
                  icon.closest('button') ||
                  icon.closest('div[role="button"]') ||
                  icon.parentElement;
        if (!t) continue;
        const r = t.getBoundingClientRect();
        if (r.width > 0 && r.height > 0 && t.offsetParent !== null) {
            t.click();
            return true;
        }
    }
    return false;
}
""")
        if not sent:
            # Playwright-level fallback using the same strict :has() selector
            sent = await self._click_first_visible([
                '[aria-label="שליחה"]:has([data-icon="wds-ic-send-filled"])',
                '[aria-label="שלח"]:has([data-icon])',
                '[aria-label="Send"]:has([data-icon])',
                'button[data-testid="send"]',
                'div[data-testid="media-confirmation-actions-send"]',
                '[data-icon="send"]',
                '[data-icon="send-light"]',
            ])
        if not sent:
            # Enter key as last resort — only accepted if the media preview then closes.
            # The preview is CONFIRMED open at this point (we waited above), so if the
            # send button is still visible after Enter, Enter did nothing useful.
            try:
                await self._page.keyboard.press("Enter")
                await asyncio.sleep(1.5)
                # The send button must have disappeared (preview closed) for Enter to count
                preview_still_open = await self._page.locator(
                    MEDIA_PREVIEW_SEND_SEL
                ).first.is_visible()
                if preview_still_open:
                    raise RuntimeError(
                        f"Could not send image to {phone}: Enter key did not close the media preview. "
                        "The message was NOT sent."
                    )
                sent = True
            except RuntimeError:
                raise
            except Exception:
                pass
        if not sent:
            raise RuntimeError("Could not find the send button in WhatsApp Web.")

        # ── Step 1: wait for the media preview overlay to close ───────────────
        # The media-preview send button disappearing means the overlay was dismissed.
        # (Using the same selectors we just clicked — they must become hidden.)
        await asyncio.sleep(0.5)  # let the send animation start
        try:
            await self._page.locator(MEDIA_PREVIEW_SEND_SEL).first.wait_for(
                state="hidden", timeout=15000
            )
        except Exception:
            # If wait_for timed out, check whether the preview is actually still open
            try:
                still_open = await self._page.locator(MEDIA_PREVIEW_SEND_SEL).first.is_visible()
            except Exception:
                still_open = False
            if still_open:
                raise RuntimeError(
                    f"Send to {phone} failed: media preview is still open after 15 s. "
                    "The message was NOT sent."
                )

        # ── Step 2: wait for the main chat compose box to reappear ────────────
        # Use selectors that are SPECIFIC to the chat compose area.
        # Deliberately excludes 'div[contenteditable][aria-placeholder]' which can
        # also match the caption input on the (now-closed, but still-in-DOM) media preview.
        chat_compose_selectors = (
            'div[contenteditable="true"][data-tab="10"], '
            'div[contenteditable="true"][data-tab="6"], '
            'footer div[contenteditable="true"], '
            'div[data-testid="conversation-compose-box-input"]'
        )
        try:
            await self._page.wait_for_selector(
                chat_compose_selectors,
                state="visible",
                timeout=15000,
            )
        except Exception:
            # Before giving up check for an invalid-number popup
            try:
                popup_visible = await self._page.locator(
                    'div[data-testid="popup-contents"], div[role="dialog"], '
                    'div[data-testid="alert-dialog"]'
                ).first.is_visible()
                if popup_visible:
                    popup_text = await self._page.locator(
                        'div[data-testid="popup-contents"], div[role="dialog"]'
                    ).first.inner_text()
                    raise ValueError(
                        f"Phone number {phone} is not on WhatsApp: {popup_text.strip()[:120]}"
                    )
            except ValueError:
                raise
            except Exception:
                pass
            raise RuntimeError(
                f"Send timed out for {phone}: WhatsApp did not return to the chat after 15 s. "
                "The message was probably NOT sent."
            )

        await asyncio.sleep(0.5)

        # ── Step 3: verify a delivery indicator exists (best-effort) ────────────
        # data-icon="msg-time" / "msg-check" / "msg-dblcheck" = sent / delivered / read
        # WhatsApp Web 2026 has NO data-testid on message container elements, so we
        # cannot scope to "last message row". Instead we verify that at least one
        # such icon is visible anywhere in the chat — if zero exist the send likely
        # failed. Steps 1 & 2 are the primary guards; this is a secondary check only.
        try:
            indicator_visible = await self._page.locator(
                '[data-icon="msg-time"], [data-icon="msg-check"], [data-icon="msg-dblcheck"]'
            ).last.is_visible()
            if not indicator_visible:
                raise RuntimeError(
                    f"No delivery indicator found after sending to {phone}. "
                    "The message was NOT sent."
                )
        except RuntimeError:
            raise
        except Exception:
            pass  # best-effort; steps 1 & 2 are the primary guards

        return True

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _click_first_visible(self, selectors: list) -> bool:
        for sel in selectors:
            try:
                el = self._page.locator(sel).first
                if await el.is_visible():
                    await el.click()
                    return True
            except Exception:
                pass
        return False

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        digits = re.sub(r"\D", "", str(phone))
        # Israeli local (05x-xxxxxxx)
        if re.match(r"^0[0-9]{9}$", digits):
            return "972" + digits[1:]
        # Israeli without leading 0 (5xxxxxxxx → 9 digits)
        if re.match(r"^[5][0-9]{8}$", digits):
            return "972" + digits
        if re.match(r"^972[0-9]{9,10}$", digits):
            return digits
        return digits
