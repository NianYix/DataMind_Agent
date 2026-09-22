@echo off
setlocal EnableExtensions EnableDelayedExpansion
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

REM --- Ollama (ensure running WITH correct models dir) ---
set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not exist "%OLLAMA_EXE%" set "OLLAMA_EXE=%ProgramFiles%\Ollama\ollama.exe"
if not exist "%OLLAMA_EXE%" (
  echo [!]  Ollama not found — skip ^(remote API mode still works^)
  goto :after_ollama
)

REM Prefer User env; fallback to E:\ollama\models when that tree exists
if not defined OLLAMA_MODELS (
  for /f "usebackq delims=" %%v in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('OLLAMA_MODELS','User')"`) do set "OLLAMA_MODELS=%%v"
)
if not defined OLLAMA_MODELS if exist "E:\ollama\models\manifests" set "OLLAMA_MODELS=E:\ollama\models"
if defined OLLAMA_MODELS echo [OK] OLLAMA_MODELS=%OLLAMA_MODELS%

REM Probe: 0=down, 1=up+models, 2=up but empty models
set "_OLLAMA_STATE=0"
for /f %%s in ('powershell -NoProfile -Command "try { $j=(Invoke-RestMethod -Uri \"http://127.0.0.1:11434/api/tags\" -TimeoutSec 2); if ($j.models -and $j.models.Count -gt 0) { 1 } else { 2 } } catch { 0 }"') do set "_OLLAMA_STATE=%%s"

if "!_OLLAMA_STATE!"=="1" (
  echo [OK] Ollama already running with models
  goto :after_ollama
)

if "!_OLLAMA_STATE!"=="2" (
  echo [!]  Ollama running but models=[] — restarting with OLLAMA_MODELS...
  taskkill /IM ollama.exe /F >nul 2>&1
  taskkill /IM "ollama app.exe" /F >nul 2>&1
  timeout /t 2 /nobreak >nul
) else (
  echo [!]  Ollama not running, starting...
)

REM Start serve ONLY with OLLAMA_MODELS in the process env.
REM Do NOT start "ollama app.exe" — the tray app often respawns serve WITHOUT OLLAMA_MODELS → models=[].
if defined OLLAMA_MODELS (
  start "Ollama" /MIN cmd /c "set OLLAMA_MODELS=%OLLAMA_MODELS%&& \"%OLLAMA_EXE%\" serve"
) else (
  start "Ollama" /MIN "%OLLAMA_EXE%" serve
)

set "_OLLAMA_READY=0"
for /L %%i in (1,1,15) do (
  if "!_OLLAMA_READY!"=="0" (
    powershell -NoProfile -Command "try { $j=Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 1; if ($j.models -and $j.models.Count -gt 0) { exit 0 } else { exit 2 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
      set "_OLLAMA_READY=1"
    ) else (
      timeout /t 1 /nobreak >nul
    )
  )
)
if "!_OLLAMA_READY!"=="1" (
  echo [OK] Ollama is ready ^(models visible^)
) else (
  echo [!]  Ollama API may still show empty models — check OLLAMA_MODELS /settings test
  echo     Tip: quit Ollama tray app if it is open; use serve started by this script
)

:after_ollama

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
echo     Ollama: serve + OLLAMA_MODELS; restart if models=[] ^(do not use empty tray serve^)
echo     Close API/Web windows to stop DataMind. Leave the Ollama serve window if needed.
echo.
pause
endlocal
