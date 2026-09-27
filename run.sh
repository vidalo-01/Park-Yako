#!/bin/bash
# Double-click (Mac) or run "./run.sh" (Linux/Mac terminal) to start the app.
# Creates a virtual environment on first run, installs Flask, then launches
# the server and opens your browser automatically.

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Setting up (first run only)..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q

# Open the browser shortly after the server starts.
( sleep 2; open http://localhost:5000 2>/dev/null || xdg-open http://localhost:5000 2>/dev/null ) &

echo "Starting Smart Gate at http://localhost:5000  (press CTRL+C to stop)"
python3 app.py
