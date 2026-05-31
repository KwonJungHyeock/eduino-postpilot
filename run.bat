@echo off
cd /d "%~dp0"
title Eduino_PostPilot

echo ============================================
echo   Eduino_PostPilot is starting...
echo.
echo   The browser opens automatically when ready.
echo   If not, open a browser and go to:  localhost:8501
echo.
echo   Keep this window OPEN. (Closing it stops the app)
echo ============================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Please run setup first ^(see README^).
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

streamlit run core\app.py

echo.
echo App stopped.
pause
