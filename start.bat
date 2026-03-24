@echo off
setlocal EnableDelayedExpansion
title WhatsApp Greeting Sender

echo.
echo  ================================================
echo   WhatsApp Greeting Sender  ^|  Local Setup
echo  ================================================
echo.

:: ── Check Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Download Python 3.10+ from https://python.org
    pause & exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo [OK] Python %%v found

:: ── Check Node.js ─────────────────────────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo         Download Node.js 18+ from https://nodejs.org
    pause & exit /b 1
)
for /f %%v in ('node --version 2^>^&1') do echo [OK] Node.js %%v found

:: ── Backend setup ─────────────────────────────────────────────────────────
cd /d "%~dp0backend"
echo.
echo [1/5] Setting up Python virtual environment...

if not exist venv (
    python -m venv venv
    if errorlevel 1 ( echo [ERROR] Failed to create venv & pause & exit /b 1 )
)
call venv\Scripts\activate.bat

echo [2/5] Installing Python dependencies...
pip install -r requirements.txt --no-warn-script-location
if errorlevel 1 ( echo [ERROR] pip install failed & pause & exit /b 1 )

echo [3/5] Installing Playwright Chromium browser...
playwright install chromium --with-deps >nul 2>&1
if errorlevel 1 playwright install chromium

:: ── Download Hebrew font (Alef) if missing ────────────────────────────────
if not exist "fonts\Alef-Regular.ttf" (
    echo [4/5] Downloading Alef Hebrew font...
    python -c "import urllib.request, os; os.makedirs('fonts',exist_ok=True); urllib.request.urlretrieve('https://github.com/alefalefalef/Alef/raw/master/fonts/Alef-Regular.ttf','fonts/Alef-Regular.ttf'); print('  Alef-Regular.ttf downloaded')" 2>nul
    if errorlevel 1 (
        echo        [WARN] Could not download Alef font. Using system fonts.
        echo        Manually place any Hebrew .ttf font in backend\fonts\
    )
) else (
    echo [4/5] Hebrew font already present.
)

:: ── Start backend ─────────────────────────────────────────────────────────
echo [5/5] Starting backend server on http://localhost:8000 ...
start "Backend - WhatsApp Greeting" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && python run.py"
timeout /t 3 /nobreak >nul

:: ── Frontend setup ────────────────────────────────────────────────────────
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo [5/5] Installing frontend dependencies ^(first run only^)...
    npm install
    if errorlevel 1 ( echo [ERROR] npm install failed & pause & exit /b 1 )
)

echo.
echo  Starting frontend on http://localhost:5173 ...
start "Frontend - WhatsApp Greeting" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 4 /nobreak >nul

echo.
echo  ================================================
echo   Application is starting!
echo.
echo   Backend  : http://localhost:8000
echo   Frontend : http://localhost:5173  ^<-- open this
echo  ================================================
echo.
start http://localhost:5173
echo  Press any key to close this launcher...
pause >nul
