# WhatsApp Greeting Sender

A **free, fully local** application that generates personalised Hebrew greeting images and sends them via WhatsApp Web automation.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Browser  (http://localhost:5173)                          │
│  React + TypeScript + Tailwind CSS (Vite)                  │
│  • Upload Excel / Image                                    │
│  • Configure text (font, size, colour, position)          │
│  • Drag-and-drop text positioning                          │
│  • Real-time progress via WebSocket                        │
└─────────────────────┬──────────────────────────────────────┘
                      │ REST + WebSocket
┌─────────────────────▼──────────────────────────────────────┐
│  FastAPI  (http://localhost:8000)                          │
│  • Excel parsing (pandas + openpyxl)                       │
│  • Image generation (Pillow + python-bidi)                 │
│  • WhatsApp automation (Playwright → WhatsApp Web)         │
│  • WebSocket broadcast for progress updates                │
└────────────────────────────────────────────────────────────┘
```

---

## Transports

The WhatsApp connection is pluggable, chosen with `WHATSAPP_TRANSPORT`:

| | `neonize` (default) | `playwright` (legacy) |
|---|---|---|
| How | WhatsApp multi-device protocol over WebSocket | Automates WhatsApp Web in Chromium |
| Browser | none | Chromium (~500 MB RAM) |
| Breaks when | the protocol changes (rare) | WhatsApp changes its UI (often) |
| Per message | sub-second | ~25 s |
| Runs in Docker | yes | no (needs a visible window for the QR) |

Both link a personal account as a paired device, so **both carry the same
account ban risk**. neonize is faster and far more stable — it is not "safer".

---

## Quick Start (Docker) — recommended

No Python, no Node, no installs.

```bash
docker run -d --name whatsapp-greeter \
  -p 8000:8000 \
  -v wa-data:/data \
  <your-dockerhub-user>/whatsapp-greeting-sender:latest
```

Open **http://localhost:8000**, click *Initialize WhatsApp*, scan the QR shown
in the page (phone → Settings → Linked Devices → Link a Device).

Or with compose:

```bash
docker compose up -d
```

**The `/data` volume is not optional.** It holds the WhatsApp pairing, generated
images, uploads and the resume log. Delete it and you re-scan the QR.

| Env var | Default | Purpose |
|---|---|---|
| `WHATSAPP_TRANSPORT` | `neonize` | `neonize` or `playwright` |
| `DEFAULT_COUNTRY_CODE` | `972` | Applied to local numbers with no country code (44 UK, 1 US/CA…) |

### Publishing to Docker Hub

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t <your-dockerhub-user>/whatsapp-greeting-sender:latest --push .
```

---

## Requirements (running from source)

| Software | Minimum version |
|---|---|
| Python | 3.10 – 3.12 |
| Node.js | 18+ |
| libmagic | for the `neonize` transport (`brew install libmagic` / `apt install libmagic1`) |
| Chrome/Chromium | only for `WHATSAPP_TRANSPORT=playwright` |

---

## Quick Start (Windows)

```bat
double-click  start.bat
```

**First run** takes ~2 minutes to install all dependencies.

## Quick Start (macOS / Linux)

```bash
chmod +x start.sh
./start.sh
```

---

## Manual Setup

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Hebrew Font Setup

The app automatically tries to download **Alef** (free Google Font) on first run.

To add fonts manually:
1. Download any Hebrew `.ttf` font (recommended: [Alef](https://fonts.google.com/specimen/Alef), [Rubik](https://fonts.google.com/specimen/Rubik), [Assistant](https://fonts.google.com/specimen/Assistant))
2. Place `.ttf` files in `backend/fonts/`
3. Restart the backend — fonts appear in the UI font selector (marked ★)

---

## Usage Walkthrough

### Step 1 — Upload Files
- **Excel file**: Column A = Name (Hebrew), Column B = Phone number
  - Israeli format: `0501234567` or `972501234567` or `+972501234567`
- **Template image**: Your greeting card (PNG/JPG recommended)

### Step 2 — Configure Text
- Choose a Hebrew font from the dropdown
- Set font size, colour, and stroke/outline
- **Drag the name label** on the live preview to position it
- The server generates an actual Pillow-rendered preview to confirm output

### Step 3 — WhatsApp Setup
- Click **Initialize WhatsApp**
- **neonize**: a QR code appears in the page — scan it from your phone
  (Settings → Linked Devices → Link a Device). Session is stored in
  `backend/whatsapp_session_neonize/`.
- **playwright**: a Chrome window opens; scan the QR there. Session is stored in
  `backend/whatsapp_session/`.

### Step 4 — Send
- Toggle **Send via WhatsApp Web** on/off
- Add an optional image caption
- Click **Send to N Contacts**
- Watch real-time progress, logs, and thumbnail results

#### Sending safely at volume

WhatsApp's spam detection, not this app, is what limits throughput. For a real
campaign (hundreds of recipients) set `delay_seconds` **and** `delay_max_seconds`
so each pause is randomised — a constant interval is itself a detection signal.
A commonly cited safe band is 30–90 s, under ~30 messages/hour, spread across
2–3 days rather than one burst.

Pass a `run_id` to make a campaign resumable: progress is written to
`backend/runs/<run_id>.json` after every delivery, and re-starting the same
`run_id` skips everyone already sent instead of messaging them twice.

---

## Excel Format Example

| Column A (Name) | Column B (Phone) |
|---|---|
| ישראל ישראלי | 0501234567 |
| שרה כהן | 972521234567 |
| דוד לוי | +972541234567 |

---

## Project Structure

```
whatsapp/
├── backend/
│   ├── main.py                   # FastAPI app, WebSocket, REST endpoints
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   ├── services/
│   │   ├── excel_service.py      # Excel parsing + phone validation
│   │   ├── image_service.py      # Pillow image generation + Hebrew BiDi
│   │   ├── whatsapp_service.py   # Playwright WhatsApp Web automation (legacy)
│   │   └── whatsapp_neonize.py   # neonize protocol transport (default)
│   ├── fonts/                    # Place Hebrew .ttf fonts here
│   ├── uploads/                  # Uploaded Excel & template images
│   ├── outputs/                  # Generated greeting images
│   ├── whatsapp_session/         # Playwright persistent browser session
│   ├── whatsapp_session_neonize/ # neonize SQLite session
│   ├── runs/                     # Per-campaign resume logs
│   ├── requirements.txt
│   └── requirements-playwright.txt  # legacy transport extras
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx               # Root component + state management
│   │   ├── components/
│   │   │   ├── ExcelUpload.tsx   # File upload + contact table
│   │   │   ├── ImageUpload.tsx   # Template image upload
│   │   │   ├── FontSettings.tsx  # Font/colour/size/align controls
│   │   │   ├── PreviewPanel.tsx  # Drag-to-position + server preview
│   │   │   ├── WhatsAppSetup.tsx # QR setup and status polling
│   │   │   ├── ProcessingPanel.tsx # Start/stop + progress bar
│   │   │   ├── ResultsPanel.tsx  # Results table with thumbnails
│   │   │   └── StatusLog.tsx     # Activity log
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts   # Auto-reconnect WebSocket hook
│   │   └── types/index.ts        # Shared TypeScript types
│   ├── package.json
│   └── vite.config.ts
│
├── Dockerfile                    # Single self-contained image (API + SPA)
├── docker-compose.yml
├── start.bat                     # Windows one-click launcher
├── start.sh                      # macOS/Linux one-click launcher
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload-excel` | Upload Excel file |
| `POST` | `/api/upload-image` | Upload template image |
| `POST` | `/api/preview` | Generate preview image |
| `GET`  | `/api/fonts` | List available fonts |
| `POST` | `/api/whatsapp/init` | Connect WhatsApp (or restart pairing) |
| `GET`  | `/api/whatsapp/status` | Login status; returns `qr_url` while pairing |
| `GET`  | `/api/health` | Liveness probe |
| `POST` | `/api/process/start` | Start processing contacts |
| `POST` | `/api/process/stop` | Stop processing |
| `GET`  | `/api/process/status` | Current processing state |
| `WS`   | `/ws/progress` | Real-time updates |

---

## Packaging (optional)

### Electron wrapper
You can wrap the frontend in Electron for a standalone `.exe`:
```bash
npm install -g electron-builder
# (add electron main.js and package config, then)
electron-builder --win
```

### PyInstaller for backend
```bash
pip install pyinstaller
pyinstaller --onefile backend/main.py
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| Hebrew text appears reversed | Ensure `python-bidi` is installed, and use a font that supports Hebrew |
| WhatsApp attachment fails | Check Playwright selectors — WhatsApp Web UI updates occasionally |
| Font not showing Hebrew | Download a Unicode Hebrew font (Alef, Rubik, Assistant) into `backend/fonts/` |
| QR code expired | Click "Restart Browser" in the WhatsApp step |
| Rate-limited by WhatsApp | Increase delay between messages to 5–10 s |

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend API | Python 3.10 + FastAPI |
| Image Processing | Pillow (PIL) + python-bidi |
| Excel Parsing | pandas + openpyxl |
| Phone Validation | phonenumbers |
| WhatsApp Automation | Playwright Chromium |
| Real-time Updates | WebSockets |
| Frontend | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| Colour Picker | react-colorful |

All components are **free and open-source**. No paid APIs or subscriptions required.
