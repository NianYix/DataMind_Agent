@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo   DataMind Agent - Start
echo ========================================
echo.

REM --- .env ---
if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo [OK] Created .env from .env.example
    echo [!]  Please edit .env and set LLM_API_KEY
  ) else (
    echo [ERROR] Missing .env and .env.example
    pause
    exit /b 1
  )
) else (
  echo [OK] Found .env
)

REM --- Python venv ---
if not exist ".venv\Scripts\python.exe" (
  echo [!]  .venv not found, creating...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv. Is Python installed?
    pause
    exit /b 1
  )
  echo [OK] Installing Python dependencies...
  call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
  )
) else (
  echo [OK] Found .venv
)

REM --- Frontend deps ---
if not exist "apps\web\node_modules" (
  echo [!]  Frontend deps missing, running pnpm install...
  where pnpm >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] pnpm not found. Install: npm install -g pnpm
    pause
    exit /b 1
  )
  pushd "apps\web"
  call pnpm install
  if errorlevel 1 (
    popd
    echo [ERROR] pnpm install failed
    pause
    exit /b 1
  )
  popd
) else (
  echo [OK] Found apps\web\node_modules
)

echo.
echo Starting backend  : http://localhost:8000
echo Starting frontend : http://localhost:3000
echo.

start "DataMind API" cmd /k "cd /d "%~dp0" && .venv\Scripts\uvicorn.exe server.main:app --reload --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
start "DataMind Web" cmd /k "cd /d "%~dp0apps\web" && pnpm dev --port 3000"

timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo [OK] Launched. Two windows: DataMind API / DataMind Web
echo     Close those windows to stop services.
echo.
pause
endlocal
