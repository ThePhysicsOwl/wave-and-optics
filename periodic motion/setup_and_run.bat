@echo off
echo ========================================================
echo   Harmonic Oscillator Lab - Setup and Execution Script
echo ========================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your PATH.
    echo Please install Python 3.10 or newer from python.org and try again.
    pause
    exit /b 1
)

:: Check if the virtual environment folder exists
if not exist "venv\" (
    echo [INFO] Virtual environment not found. Creating a new one...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate the virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

:: Upgrade pip to avoid installation errors
echo [INFO] Ensuring pip is up-to-date...
python -m pip install --upgrade pip >nul 2>&1

:: Install dependencies
echo [INFO] Installing required dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)

:: Run the application
echo [INFO] Launching Harmonic Oscillator Lab...
python main.py

:: Deactivate when closed
deactivate
