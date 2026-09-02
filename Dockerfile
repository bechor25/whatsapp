# Single self-contained image: FastAPI serves both the API and the built SPA.
# No browser is involved — the neonize transport speaks the WhatsApp protocol
# directly, so this runs headless with no Chromium, no X11 and no display.
#
# Build (multi-arch, push to Docker Hub):
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     -t <user>/whatsapp-greeting-sender:latest --push .
#
# Run:
#   docker run -p 8000:8000 -v wa-session:/data <user>/whatsapp-greeting-sender

# ── Stage 1: build the frontend ───────────────────────────────────────────────
FROM --platform=$BUILDPLATFORM node:20-alpine AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim

# libmagic1 = neonize media type detection; fonts-* give a Hebrew fallback so
# the image renders correctly even before Alef is downloaded.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
        curl \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /build/dist ./static

# Bundle the Hebrew font at build time so a running container needs no network.
# Verified by actually loading it with PIL: the old download URL 404'd and
# silently saved an HTML error page as the .ttf, which only failed at render time.
RUN mkdir -p fonts \
    && curl -fsSL -o fonts/Alef-Regular.ttf \
       "https://github.com/google/fonts/raw/main/ofl/alef/Alef-Regular.ttf" \
    && python -c "from PIL import ImageFont; ImageFont.truetype('fonts/Alef-Regular.ttf', 24)"

# Writable state lives under /data so a single volume persists everything that
# matters: the WhatsApp pairing (else you re-scan the QR on every restart),
# generated images, uploads, and the resume log for interrupted campaigns.
ENV WHATSAPP_TRANSPORT=neonize \
    DEFAULT_COUNTRY_CODE=972 \
    FRONTEND_DIST=/app/static \
    PYTHONUNBUFFERED=1

RUN mkdir -p /data/whatsapp_session_neonize /data/outputs /data/uploads /data/runs \
    && rm -rf whatsapp_session_neonize outputs uploads runs \
    && ln -s /data/whatsapp_session_neonize whatsapp_session_neonize \
    && ln -s /data/outputs outputs \
    && ln -s /data/uploads uploads \
    && ln -s /data/runs runs

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
