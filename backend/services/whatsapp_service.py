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
        # Strategy 1 (fastest): WhatsApp Web always keeps a hidden input[type="file"]
        # in the DOM. Playwright's set_input_files works on hidden inputs directly
        # without needing to click any button.
        file_set = False
        for selector in [
            'input[accept="image/*"]',
            'input[accept*="image"][type="file"]',
            'input[type="file"]',
        ]:
            try:
                el = self._page.locator(selector).first
                if await el.count() > 0:
                    await el.set_input_files(abs_path)
                    file_set = True
                    break
            except Exception:
                pass

        if not file_set:
            # Strategy 2: click the "+" / attach button, then retry the input.
            # DOM inspection (2026) shows the icon is "plus-rounded".
            await self._click_first_visible([
                '[data-icon="plus-rounded"]',
                '[data-icon="attach-menu-plus"]',
                '[data-icon="clip"]',
                '[data-icon="attach"]',
                'button[aria-label="צרף"]',
                'button[aria-label="Attach"]',
                'button[data-testid="compose-btn-attachment"]',
                'span[data-testid="attach-btn"]',
            ])
            await asyncio.sleep(0.5)

            # After the menu opens, try clicking "Photos, GIF, Videos" entry
            await self._click_first_visible([
                'li[data-testid="mi-attach-image"]',
                '[data-icon="image"]',
            ])
            await asyncio.sleep(0.4)

            for selector in [
                'input[accept="image/*"]',
                'input[accept*="image"][type="file"]',
                'input[type="file"]',
            ]:
                try:
                    el = self._page.locator(selector).first
                    if await el.count() > 0:
                        await el.set_input_files(abs_path)
                        file_set = True
                        break
                except Exception:
                    pass

        if not file_set:
            # Strategy 3: expose hidden input via JS then set files
            try:
                await self._page.evaluate(
                    "() => document.querySelectorAll('input[type=\"file\"]')"
                    ".forEach(e => { e.style.display='block'; e.style.opacity='1'; })"
                )
                await asyncio.sleep(0.2)
                el = self._page.locator('input[type="file"]').first
                if await el.count() > 0:
                    await el.set_input_files(abs_path)
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

        await asyncio.sleep(2.0)  # wait for image preview to appear

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
        # WhatsApp Web 2026 (Hebrew): the media-preview send button has
        #   aria-label="שליחה"  and  data-icon="wds-ic-send-filled"
        sent = await self._click_first_visible(
            [
                # Actual Hebrew UI labels found in DOM (2026)
                'div[aria-label="שליחה"]',
                '[data-icon="wds-ic-send-filled"]',
                'button[aria-label="שליחה"]',
                'span[aria-label="שליחה"]',
                # English / legacy variants
                'div[aria-label="שלח"]',
                'div[aria-label="Send"]',
                'button[aria-label="שלח"]',
                'button[aria-label="Send"]',
                'span[aria-label="שלח"]',
                'span[aria-label="Send"]',
                # data-testid variants
                'button[data-testid="send"]',
                'span[data-testid="send"]',
                'div[data-testid="send"]',
                # data-icon legacy variants
                '[data-icon="send"]',
                '[data-icon="send-light"]',
            ]
        )
        if not sent:
            # Specific media-confirmation container
            try:
                btn = self._page.locator('div[data-testid="media-confirmation-actions-send"]').first
                if await btn.is_visible():
                    await btn.click()
                    sent = True
            except Exception:
                pass
        if not sent:
            # Enter key as last resort — only accepted if the media preview then closes
            try:
                await self._page.keyboard.press("Enter")
                await asyncio.sleep(1.2)
                # If the media-preview send button is STILL visible, Enter did nothing
                preview_still_open = await self._page.locator(
                    '[data-icon="wds-ic-send-filled"], div[aria-label="שליחה"], button[aria-label="שליחה"]'
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
        media_preview_selector = (
            '[data-icon="wds-ic-send-filled"], '
            'div[aria-label="שליחה"], button[aria-label="שליחה"]'
        )
        try:
            await self._page.locator(media_preview_selector).first.wait_for(
                state="hidden", timeout=15000
            )
        except Exception:
            # If wait_for timed out, check whether the preview is actually still open
            try:
                still_open = await self._page.locator(media_preview_selector).first.is_visible()
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

        # ── Step 3: verify a delivery indicator is visible ────────────────────
        # data-icon="msg-time"     → clock  (pending / just sent to server)
        # data-icon="msg-check"    → ✓      (sent to server)
        # data-icon="msg-dblcheck" → ✓✓     (delivered / read)
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
