@echo off
cd /d "%~dp0"
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)
python -c "import app" 2>nul
if errorlevel 1 (
  echo App failed to import. Details:
  python -c "import app"
  pause
  exit /b 1
)
start "" pythonw "%~dp0app.py"
