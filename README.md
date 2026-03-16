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

## Requirements

| Software | Minimum version |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| Chrome/Chromium | any (Playwright downloads one) |

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
- Click **Launch WhatsApp Browser** — a Chrome window opens
- Scan the QR code with your phone's WhatsApp app
- Session is saved in `backend/whatsapp_session/` — no re-scan needed next time

### Step 4 — Send
- Toggle **Send via WhatsApp Web** on/off
- Set a delay between messages (3–5 s recommended to avoid blocking)
- Add an optional image caption
- Click **Send to N Contacts**
- Watch real-time progress, logs, and thumbnail results

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
│   │   └── whatsapp_service.py   # Playwright WhatsApp Web automation
│   ├── fonts/                    # Place Hebrew .ttf fonts here
│   ├── uploads/                  # Uploaded Excel & template images
│   ├── outputs/                  # Generated greeting images
│   ├── whatsapp_session/         # Playwright persistent browser session
│   └── requirements.txt
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
| `POST` | `/api/whatsapp/init` | Launch WhatsApp browser |
| `GET`  | `/api/whatsapp/status` | Check login status |
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
