@echo off
REM Double-click this file to start the app on Windows.
REM Creates a virtual environment on first run, installs Flask, then
REM launches the server and opens your browser automatically.

cd /d %~dp0

if not exist venv (
    echo Setting up (first run only)...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt -q

start "" http://localhost:5000
echo Starting Smart Gate at http://localhost:5000  (close this window to stop)
python app.py
