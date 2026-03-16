#!/usr/bin/env bash
set -e

echo ""
echo " ================================================"
echo "  WhatsApp Greeting Sender  |  Local Setup"
echo " ================================================"
echo ""

# ── Check Python ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "[ERROR] Python 3 is not installed. Install from https://python.org"
  exit 1
fi
echo "[OK] $(python3 --version) found"

# ── Check Node.js ─────────────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
  echo "[ERROR] Node.js is not installed. Install from https://nodejs.org"
  exit 1
fi
echo "[OK] Node.js $(node --version) found"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Backend setup ─────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/backend"
echo ""
echo "[1/5] Setting up Python virtual environment..."

if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate

echo "[2/5] Installing Python dependencies..."
pip install -r requirements.txt

echo "[3/5] Installing Playwright Chromium..."
playwright install chromium

# ── Download Hebrew font ──────────────────────────────────────────────────────
mkdir -p fonts
if [ ! -f fonts/Alef-Regular.ttf ]; then
  echo "[4/5] Downloading Alef Hebrew font..."
  python3 -c "
import urllib.request
urllib.request.urlretrieve(
    'https://github.com/alefalefalef/Alef/raw/master/fonts/Alef-Regular.ttf',
    'fonts/Alef-Regular.ttf'
)
print('  Alef-Regular.ttf downloaded')
" 2>/dev/null || echo "       [WARN] Could not download Alef font. Place a Hebrew .ttf in backend/fonts/"
else
  echo "[4/5] Hebrew font already present."
fi

# ── Start backend ─────────────────────────────────────────────────────────────
echo "[5/5] Starting backend on http://localhost:8000 ..."
uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 2

# ── Frontend setup ────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/frontend"
if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo ""
echo "Starting frontend on http://localhost:5173 ..."
npm run dev &
FRONTEND_PID=$!
sleep 3

echo ""
echo " ================================================"
echo "  Application is running!"
echo ""
echo "  Backend  : http://localhost:8000"
echo "  Frontend : http://localhost:5173  <-- open this"
echo " ================================================"
echo ""
echo "Press Ctrl+C to stop everything."

# Open browser
if command -v open &>/dev/null; then
  open http://localhost:5173
elif command -v xdg-open &>/dev/null; then
  xdg-open http://localhost:5173
fi

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
