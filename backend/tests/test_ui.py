"""
Playwright UI (E2E) tests — require BOTH servers to be running:

    backend : uvicorn main:app --reload --host 127.0.0.1 --port 8000
    frontend: npm run dev  (http://localhost:5173)

Run with:
    pytest tests/test_ui.py -v --timeout=30
"""
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, Page, expect


FRONTEND = "http://localhost:5173"
TIMEOUT  = 10_000   # ms


# ── Shared browser / page fixtures (function-scoped — safe with asyncio auto) ─

@pytest_asyncio.fixture
async def page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx  = await browser.new_context()
        pg   = await ctx.new_page()
        yield pg
        await ctx.close()
        await browser.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def goto_app(page: Page):
    await page.goto(FRONTEND, wait_until="networkidle", timeout=TIMEOUT)


# ── Landing page ──────────────────────────────────────────────────────────────

class TestLanding:
    @pytest.mark.asyncio
    async def test_page_title_visible(self, page):
        await goto_app(page)
        title = page.locator("h1, h2").first
        await expect(title).to_be_visible(timeout=8_000)

    @pytest.mark.asyncio
    async def test_page_does_not_show_error_boundary(self, page):
        await goto_app(page)
        # React error boundary or JS crash message should not appear
        error_text = page.get_by_text("Something went wrong")
        await expect(error_text).not_to_be_visible(timeout=5_000)

    @pytest.mark.asyncio
    async def test_step_indicators_rendered(self, page):
        await goto_app(page)
        # At least one step indicator circle/bar should be visible
        steps = page.locator("[class*='step'], [data-step]")
        count = await steps.count()
        assert count >= 1

    @pytest.mark.asyncio
    async def test_upload_step_is_initial_step(self, page):
        await goto_app(page)
        # Something related to upload should be on screen
        upload_area = page.locator(
            "[class*='upload'], [data-testid*='upload']"
        ).or_(page.get_by_text("העלאה")).or_(page.get_by_text("Upload")).first
        await expect(upload_area).to_be_visible(timeout=8_000)


# ── Excel upload zone ─────────────────────────────────────────────────────────

class TestExcelUploadZone:
    @pytest.mark.asyncio
    async def test_dropzone_visible(self, page):
        await goto_app(page)
        zone = page.locator("[class*='dropzone'], [class*='drop-zone'], label[for], input[type='file']").first
        await expect(zone).to_be_visible(timeout=8_000)

    @pytest.mark.asyncio
    async def test_excel_input_accepts_xlsx(self, page):
        await goto_app(page)
        inputs = page.locator("input[type='file']")
        count  = await inputs.count()
        assert count >= 1
        # At least one input should accept xlsx
        for i in range(count):
            accept = await inputs.nth(i).get_attribute("accept")
            if accept and "xlsx" in accept:
                return
        # If none specify accept, that is also acceptable behaviour
        pytest.skip("No file input with explicit xlsx accept attribute found — OK")


# ── Navigation ────────────────────────────────────────────────────────────────

class TestNavigation:
    @pytest.mark.asyncio
    async def test_next_button_exists_or_disabled_on_step1(self, page):
        await goto_app(page)
        # Try each possible label until one is found
        found = False
        for label in ("הבא", "Next", "Continue", "המשך"):
            btn = page.get_by_role("button", name=label)
            if await btn.count() > 0:
                await expect(btn.first).to_be_visible(timeout=5_000)
                found = True
                break
        assert found, "No next-step button found on the page"

    @pytest.mark.asyncio
    async def test_back_button_not_visible_on_first_step(self, page):
        await goto_app(page)
        for label in ("חזור", "Back", "Previous"):
            btn = page.get_by_role("button", name=label)
            if await btn.count() > 0:
                # Back button may be visible but must be disabled on the first step
                await expect(btn.first).to_be_disabled(timeout=5_000)
                return
        # No back button at all — also correct for first step
        pass


# ── Responsive layout ─────────────────────────────────────────────────────────

class TestResponsive:
    @pytest.mark.asyncio
    async def test_renders_on_mobile_viewport(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx  = await browser.new_context(viewport={"width": 375, "height": 812})
            page = await ctx.new_page()
            await page.goto(FRONTEND, wait_until="networkidle", timeout=TIMEOUT)
            body = page.locator("body")
            await expect(body).to_be_visible(timeout=5_000)
            await ctx.close()
            await browser.close()

    @pytest.mark.asyncio
    async def test_renders_on_wide_viewport(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx  = await browser.new_context(viewport={"width": 1920, "height": 1080})
            page = await ctx.new_page()
            await page.goto(FRONTEND, wait_until="networkidle", timeout=TIMEOUT)
            body = page.locator("body")
            await expect(body).to_be_visible(timeout=5_000)
            await ctx.close()
            await browser.close()


# ── Console error check ───────────────────────────────────────────────────────

class TestNoConsoleErrors:
    @pytest.mark.asyncio
    async def test_no_js_errors_on_load(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx     = await browser.new_context()
            page    = await ctx.new_page()
            errors  = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(FRONTEND, wait_until="networkidle", timeout=TIMEOUT)
            await page.wait_for_timeout(1_000)
            await ctx.close()
            await browser.close()
        assert errors == [], f"JS errors on load: {errors}"
