#!/bin/bash
set -e

# Change to the directory of the script
cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Download Spacy model
echo "Downloading Spacy model..."
# check if model is installed, or just run it (it's fast if already there)
python -m spacy download en_core_web_lg

# Start Redis if not running (simple check)
# This assumes redis-server is in path. If not, the user needs to make sure it's running.
# We won't force start it because it might be a system service, but we can warn.
if ! redis-cli ping > /dev/null 2>&1; then
    echo "WARNING: Redis is not reachable. Attempting to start local redis-server..."
    if command -v redis-server >/dev/null 2>&1; then
        redis-server --daemonize yes
    else
        echo "ERROR: redis-server not found. Please install or start Redis manually."
        # We don't exit, we let the app fail if it must, or maybe the user has it elsewhere.
    fi
fi

# Start the server
echo "Starting FastAPI server..."
uvicorn main:app --reload --port 8000
