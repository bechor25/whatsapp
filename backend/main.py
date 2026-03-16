import asyncio
import os
import sys
import shutil
import uuid
from datetime import datetime
from typing import Dict, List

# ── Windows event-loop fix ────────────────────────────────────────────────────
# uvicorn on Windows defaults to SelectorEventLoop which does NOT support
# subprocess creation (required by Playwright). Force ProactorEventLoop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ─────────────────────────────────────────────────────────────────────────────

import aiofiles
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image

from models.schemas import PreviewRequest, ProcessRequest, TextConfig
from services.excel_service import ExcelService
from services.image_service import ImageService
from services.whatsapp_service import WhatsAppService

# ── Directories ───────────────────────────────────────────────────────────────
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
FONTS_DIR  = "fonts"
SESSION_DIR = "whatsapp_session"

for _d in (UPLOAD_DIR, OUTPUT_DIR, FONTS_DIR, SESSION_DIR):
    os.makedirs(_d, exist_ok=True)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="WhatsApp Greeting Sender", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR),  name="uploads")

# ── Services ──────────────────────────────────────────────────────────────────
excel_service    = ExcelService()
image_service    = ImageService(FONTS_DIR)
whatsapp_service = WhatsAppService(SESSION_DIR)

# ── Processing state ──────────────────────────────────────────────────────────
class _State:
    def __init__(self):
        self.is_processing = False
        self.stop_requested = False
        self.total = 0
        self.completed = 0
        self.failed = 0
        self.current = ""
        self.results: List[Dict] = []
        self.logs: List[Dict] = []

    def reset(self):
        self.__init__()

    def to_dict(self) -> Dict:
        return {
            "isProcessing": self.is_processing,
            "total":        self.total,
            "completed":    self.completed,
            "failed":       self.failed,
            "current":      self.current,
            "results":      self.results,
            "logs":         self.logs,
        }

state = _State()

# ── WebSocket manager ─────────────────────────────────────────────────────────
class _Manager:
    def __init__(self):
        self._connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self._connections = [c for c in self._connections if c is not ws]

    async def broadcast(self, data: dict):
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = _Manager()

# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only .xlsx / .xls files are supported.")

    fname = f"excel_{uuid.uuid4().hex[:8]}.xlsx"
    path  = os.path.join(UPLOAD_DIR, fname)

    async with aiofiles.open(path, "wb") as fh:
        await fh.write(await file.read())

    try:
        contacts, errors = excel_service.parse_excel(path)
        return {
            "success":  True,
            "filePath": path,
            "contacts": contacts,
            "errors":   errors,
            "total":    len(contacts),
        }
    except Exception as exc:
        os.remove(path)
        raise HTTPException(400, str(exc))


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    allowed = {"image/jpeg", "image/jpg", "image/png", "image/bmp", "image/gif", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, f"Unsupported image type: {file.content_type}")

    ext   = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "png"
    fname = f"template_{uuid.uuid4().hex[:8]}.{ext}"
    path  = os.path.join(UPLOAD_DIR, fname)

    async with aiofiles.open(path, "wb") as fh:
        await fh.write(await file.read())

    try:
        with Image.open(path) as img:
            width, height = img.size
    except Exception as exc:
        os.remove(path)
        raise HTTPException(400, f"Invalid image: {exc}")

    # Copy to /outputs so it can be served statically
    shutil.copy2(path, os.path.join(OUTPUT_DIR, fname))

    return {
        "success":  True,
        "filePath": path,
        "url":      f"/outputs/{fname}",
        "width":    width,
        "height":   height,
    }


@app.post("/api/preview")
async def generate_preview(req: PreviewRequest):
    if not os.path.exists(req.image_path):
        raise HTTPException(404, "Template image not found.")

    name    = f"preview_{uuid.uuid4().hex[:8]}.png"
    outpath = os.path.join(OUTPUT_DIR, name)

    try:
        image_service.generate_image(
            template_path=req.image_path,
            name=req.sample_name or "שם לדוגמה",
            output_path=outpath,
            text_config=req.text_config,
        )
        return {"success": True, "previewUrl": f"/outputs/{name}"}
    except Exception as exc:
        raise HTTPException(500, f"Preview failed: {exc}")


@app.get("/api/fonts")
async def get_fonts():
    return {"fonts": image_service.get_available_fonts()}


@app.post("/api/whatsapp/init")
async def init_whatsapp():
    return await whatsapp_service.initialize()


@app.get("/api/whatsapp/status")
async def whatsapp_status():
    return await whatsapp_service.check_status()


@app.get("/api/whatsapp/debug-dom")
async def debug_dom(phone: str = "972542160685"):
    """Navigate to a chat and dump all interactive elements — helps diagnose UI changes."""
    page = whatsapp_service._page
    if not page:
        raise HTTPException(400, "WhatsApp not initialized")
    try:
        await page.goto(
            f"https://web.whatsapp.com/send?phone={phone}",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        import asyncio as _a
        await _a.sleep(6)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "wa_debug.png"))
        elements = await page.evaluate('''() => {
            const res = [];
            document.querySelectorAll("button,div[role=button],span[role=button]").forEach(el => {
                res.push({tag: el.tagName, text: el.innerText?.trim().slice(0,40),
                    title: el.title, aria: el.getAttribute("aria-label"),
                    testid: el.getAttribute("data-testid"), class: el.className?.slice(0,60)});
            });
            document.querySelectorAll("[data-icon]").forEach(el => {
                res.push({tag: el.tagName, icon: el.getAttribute("data-icon"),
                    testid: el.getAttribute("data-testid"), aria: el.getAttribute("aria-label"),
                    parent_testid: el.parentElement?.getAttribute("data-testid")});
            });
            document.querySelectorAll("input[type=file]").forEach(el => {
                res.push({tag: "INPUT[file]", accept: el.accept, name: el.name,
                    visible: el.offsetParent !== null, display: getComputedStyle(el).display});
            });
            return res;
        }''')
        return {"count": len(elements), "elements": elements}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/process/start")
async def start_processing(req: ProcessRequest, bg: BackgroundTasks):
    if state.is_processing:
        raise HTTPException(400, "Already processing. Stop the current run first.")
    state.reset()
    bg.add_task(_run, req)
    return {"success": True, "message": "Processing started."}


@app.post("/api/process/stop")
async def stop_processing():
    state.stop_requested = True
    return {"success": True}


@app.get("/api/process/status")
async def process_status():
    return state.to_dict()


@app.websocket("/ws/progress")
async def ws_progress(ws: WebSocket):
    await manager.connect(ws)
    await ws.send_json({"type": "state", "data": state.to_dict()})
    try:
        while True:
            await asyncio.sleep(1)
            await ws.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)


# ── Background processing ─────────────────────────────────────────────────────

async def _run(req: ProcessRequest):
    state.is_processing  = True
    state.total          = len(req.contacts)
    state.stop_requested = False

    await manager.broadcast({"type": "start", "data": state.to_dict()})

    for i, contact in enumerate(req.contacts):
        if state.stop_requested:
            _log(state, "Processing stopped by user.", "warning")
            break

        name  = contact.name
        phone = contact.phone
        state.current = f"Generating image for {name}…"

        result: Dict = {
            "index":    i + 1,
            "name":     name,
            "phone":    phone,
            "imageUrl": None,
            "status":   "processing",
            "error":    None,
        }
        state.results.append(result)
        await manager.broadcast({"type": "update", "data": state.to_dict()})

        try:
            out_name = f"greeting_{i + 1:04d}_{uuid.uuid4().hex[:6]}.png"
            out_path = os.path.join(OUTPUT_DIR, out_name)

            image_service.generate_image(
                template_path=req.image_path,
                name=name,
                output_path=out_path,
                text_config=req.text_config,
            )
            result["imageUrl"] = f"/outputs/{out_name}"

            if req.send_whatsapp:
                state.current = f"Sending to {name} ({phone})…"
                await manager.broadcast({"type": "update", "data": state.to_dict()})
                await whatsapp_service.send_image(
                    phone=phone,
                    image_path=out_path,
                    caption=req.caption or "",
                )
                result["status"] = "sent"
                state.completed += 1
                _log(state, f"✓ Sent to {name} ({phone})", "success")
            else:
                result["status"] = "generated"
                state.completed += 1
                _log(state, f"✓ Image generated for {name}", "success")

        except Exception as exc:
            result["status"] = "failed"
            result["error"]  = str(exc)
            state.failed    += 1
            _log(state, f"✗ Failed for {name} ({phone}): {exc}", "error")

        await manager.broadcast({"type": "update", "data": state.to_dict()})

        # Configurable delay between sends
        if req.send_whatsapp and req.delay_seconds > 0 and i < len(req.contacts) - 1:
            state.current = f"Waiting {req.delay_seconds}s before next message…"
            await manager.broadcast({"type": "update", "data": state.to_dict()})
            await asyncio.sleep(req.delay_seconds)

    state.is_processing = False
    state.current       = "Done ✓"
    await manager.broadcast({"type": "complete", "data": state.to_dict()})


def _log(s: _State, message: str, status: str):
    s.logs.append(
        {
            "time":    datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "status":  status,
        }
    )
