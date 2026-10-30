@echo off
chcp 65001 >nul
title Glacier Installer
cd /d "%~dp0"
echo ==============================================
echo   Glacier V4 - Installer
echo ==============================================

set PYCMD=
py -3.12 --version >nul 2>&1 && set PYCMD=py -3.12
if "%PYCMD%"=="" (
  py -3.13 --version >nul 2>&1 && set PYCMD=py -3.13
)
if "%PYCMD%"=="" (
  python --version >nul 2>&1 && set PYCMD=python
)
if "%PYCMD%"=="" (
  echo [ERROR] Python nahi mila. python.org se Python 3.12 install karo ("Add to PATH" tick karna^), phir dobara chalao.
  pause & exit /b 1
)
echo Python: %PYCMD%

if not exist .venv (
  echo Virtual environment bana raha hoon...
  %PYCMD% -m venv .venv || (echo [ERROR] venv nahi bana & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
echo Libraries install ho rahi hain (5-10 minute lag sakte hain, faster-whisper bada hai^)...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [WARN] Kuchh libraries fail hui. Ek ek karke koshish karta hoon...
  for /f "usebackq eol=# tokens=1" %%p in ("requirements.txt") do python -m pip install %%p
)

echo.
set /p OPT=Browser control (Playwright^) bhi install karun? [y/N]:
if /i "%OPT%"=="y" (
  python -m pip install playwright
  python -m playwright install chromium
)

if not exist .env (
  copy .env.example .env >nul
  echo .env bana di. Notepad khul raha hai - GEMINI_API_KEY daalo, save karo, band karo.
  notepad .env
)

echo.
python doctor.py
echo.
echo ==============================================
echo  Taiyar! Glacier chalane ke liye run.bat double-click karo.
echo  Laptop on hote hi apne-aap chalu karna ho to:  .venv\Scripts\python setup_autostart.py
echo ==============================================
pause
