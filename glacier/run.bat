@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
  echo Pehle install.bat chalao.
  pause & exit /b 1
)
start "" .venv\Scripts\pythonw.exe main_gui.py
