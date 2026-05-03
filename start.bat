@echo off
setlocal enabledelayedexpansion
set ERRORS=0
set VENV_DIR=%~dp0venv

echo ============================================================
echo  Monster Advancer - Startup Check
echo ============================================================
echo.

:: ─── 1. Python ───────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [MISSING] Python is not installed or not on PATH.
    echo          Install: https://www.python.org/downloads/
    echo          Make sure to check "Add Python to PATH" during install.
    echo.
    set ERRORS=1
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK]      %%v
)

:: ─── 2. pip ──────────────────────────────────────────────────
pip --version >nul 2>&1
if errorlevel 1 (
    echo [MISSING] pip is not available.
    echo          Fix:     python -m ensurepip --upgrade
    echo.
    set ERRORS=1
) else (
    echo [OK]      pip found
)

:: ─── 3. venv module ──────────────────────────────────────────
python -c "import venv" >nul 2>&1
if errorlevel 1 (
    echo [MISSING] Python venv module is not available.
    echo          Fix:     pip install virtualenv
    echo          Then:    virtualenv venv
    echo.
    set ERRORS=1
) else (
    echo [OK]      venv module available
)

:: ─── 4. Virtual environment folder ───────────────────────────
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [MISSING] Virtual environment not found at: venv\
    echo          Fix:     python -m venv venv
    echo          Then:    venv\Scripts\pip install -r backend\requirements.txt
    echo.
    set ERRORS=1
) else (
    echo [OK]      Virtual environment found
)

:: ─── 5. fastapi (inside venv) ────────────────────────────────
if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" -c "import fastapi" >nul 2>&1
    if errorlevel 1 (
        echo [MISSING] fastapi is not installed in the virtual environment.
        echo          Fix:     venv\Scripts\pip install fastapi
        echo.
        set ERRORS=1
    ) else (
        echo [OK]      fastapi installed
    )
)

:: ─── 6. uvicorn (inside venv) ────────────────────────────────
if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" -c "import uvicorn" >nul 2>&1
    if errorlevel 1 (
        echo [MISSING] uvicorn is not installed in the virtual environment.
        echo          Fix:     venv\Scripts\pip install uvicorn[standard]
        echo.
        set ERRORS=1
    ) else (
        echo [OK]      uvicorn installed
    )
)

:: ─── 7. sqlalchemy (inside venv) ─────────────────────────────
if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" -c "import sqlalchemy" >nul 2>&1
    if errorlevel 1 (
        echo [MISSING] sqlalchemy is not installed in the virtual environment.
        echo          Fix:     venv\Scripts\pip install sqlalchemy
        echo.
        set ERRORS=1
    ) else (
        echo [OK]      sqlalchemy installed
    )
)

:: ─── 8. Database files ────────────────────────────────────────
if not exist "%~dp0backend\data\monsters.db" (
    echo [MISSING] monsters.db not found at backend\data\monsters.db
    echo          Fix:     venv\Scripts\python backend\data\build_db.py
    echo.
    set ERRORS=1
) else (
    echo [OK]      monsters.db found
)
if not exist "%~dp0backend\data\prod.db" (
    echo [MISSING] prod.db not found at backend\data\prod.db
    echo          Fix:     venv\Scripts\python backend\data\build_db.py
    echo.
    set ERRORS=1
) else (
    echo [OK]      prod.db found
)

echo.
echo ============================================================

if !ERRORS! NEQ 0 (
    echo  [!] One or more requirements are missing. See above.
    echo      Fix all issues then re-run this script.
    echo ============================================================
    echo.
    pause
    exit /b 1
)

echo  All checks passed. Starting server...
echo ============================================================
echo.
echo  API:      http://localhost:8000
echo  Docs:     http://localhost:8000/docs
echo  Frontend: open frontend\index.html in your browser
echo.

cd /d "%~dp0backend"
..\venv\Scripts\uvicorn app.main:app --reload --port 8000
