#!/bin/bash
echo "========================================================"
echo "  Harmonic Oscillator Lab - Setup and Execution Script"
echo "========================================================"
echo ""

# Check for python3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is not installed or not in your PATH."
    echo "Please install Python 3.10+ and try again."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "[INFO] Virtual environment not found. Creating a new one..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        exit 1
    fi
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "[INFO] Ensuring pip is up-to-date..."
pip install --upgrade pip >/dev/null 2>&1

# Install requirements
echo "[INFO] Installing required dependencies from requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    exit 1
fi

# Run the app
echo "[INFO] Launching Harmonic Oscillator Lab..."
python main.py

# Deactivate
deactivate
