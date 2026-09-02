#!/usr/bin/env bash
set -e

echo ""
echo " ================================================"
echo "  WhatsApp Greeting Sender  |  Local Setup"
echo " ================================================"
echo ""

# Transport: neonize (protocol library, no browser) or playwright (WhatsApp Web).
# Override by exporting it before running:  WHATSAPP_TRANSPORT=playwright ./start.sh
WHATSAPP_TRANSPORT="${WHATSAPP_TRANSPORT:-neonize}"
# Country code applied to local numbers without one (972 = Israel, 44 = UK, …).
DEFAULT_COUNTRY_CODE="${DEFAULT_COUNTRY_CODE:-972}"
export WHATSAPP_TRANSPORT DEFAULT_COUNTRY_CODE

# ── Pick a supported Python ───────────────────────────────────────────────────
# The pinned dependencies do not build on 3.13+, so prefer a known-good version
# and fall back to whatever python3 is on PATH.
PY=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" &>/dev/null; then
    ver=$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    major=${ver%%.*}; minor=${ver##*.}
    if [ "$major" = "3" ] && [ "$minor" -ge 10 ] && [ "$minor" -le 12 ]; then
      PY="$candidate"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  echo "[ERROR] Need Python 3.10-3.12. Found: $(python3 --version 2>&1 || echo none)"
  echo "        Install one, e.g.:  brew install python@3.12"
  exit 1
fi
echo "[OK] $($PY --version) found ($PY)"

# ── Check Node.js ─────────────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
  echo "[ERROR] Node.js is not installed. Install from https://nodejs.org"
  exit 1
fi
echo "[OK] Node.js $(node --version) found"

# ── libmagic (required by neonize for media type detection) ───────────────────
if [ "$WHATSAPP_TRANSPORT" = "neonize" ]; then
  if ! ( [ -e /opt/homebrew/lib/libmagic.dylib ] || [ -e /usr/local/lib/libmagic.dylib ] \
      || [ -e /usr/lib/x86_64-linux-gnu/libmagic.so.1 ] || ldconfig -p 2>/dev/null | grep -q libmagic ); then
    echo "[WARN] libmagic not found — neonize needs it."
    if command -v brew &>/dev/null; then
      echo "       Installing via Homebrew..."
      brew install libmagic
    else
      echo "       Install it:  sudo apt-get install -y libmagic1   (Debian/Ubuntu)"
      exit 1
    fi
  fi
  echo "[OK] libmagic present"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Backend setup ─────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/backend"
echo ""
echo "[1/5] Setting up Python virtual environment..."

if [ ! -d venv ]; then
  "$PY" -m venv venv
fi
source venv/bin/activate

echo "[2/5] Installing Python dependencies..."
pip install -q --upgrade pip
if [ "$WHATSAPP_TRANSPORT" = "playwright" ]; then
  pip install -q -r requirements-playwright.txt
else
  pip install -q -r requirements.txt
fi

if [ "$WHATSAPP_TRANSPORT" = "playwright" ]; then
  echo "[3/5] Installing Playwright Chromium..."
  playwright install chromium
else
  echo "[3/5] Skipping Chromium (transport=$WHATSAPP_TRANSPORT, no browser needed)."
fi

# ── Hebrew font ───────────────────────────────────────────────────────────────
mkdir -p fonts
if [ ! -s fonts/Alef-Regular.ttf ]; then
  echo "[4/5] Downloading Alef Hebrew font..."
  # Google Fonts mirror — the old alefalefalef/Alef path 404s and silently
  # saves an HTML error page as the .ttf.
  curl -fsSL -o fonts/Alef-Regular.ttf \
    "https://github.com/google/fonts/raw/main/ofl/alef/Alef-Regular.ttf" \
  && file fonts/Alef-Regular.ttf | grep -q "TrueType" \
  && echo "       Alef-Regular.ttf downloaded" \
  || { rm -f fonts/Alef-Regular.ttf
       echo "       [WARN] Download failed. Place any Hebrew .ttf in backend/fonts/"; }
else
  echo "[4/5] Hebrew font already present."
fi

# ── Start backend ─────────────────────────────────────────────────────────────
echo "[5/5] Starting backend on http://localhost:8000  (transport: $WHATSAPP_TRANSPORT)"
uvicorn main:app --host 127.0.0.1 --port 8000 &
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
echo "  Transport: $WHATSAPP_TRANSPORT"
echo " ================================================"
echo ""
echo "Press Ctrl+C to stop everything."

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' EXIT INT TERM

# Open browser
if command -v open &>/dev/null; then
  open http://localhost:5173
elif command -v xdg-open &>/dev/null; then
  xdg-open http://localhost:5173
fi

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
