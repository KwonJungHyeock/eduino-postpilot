@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Eduino_PostPilot

echo ============================================
echo   Eduino_PostPilot 실행 중...
echo   이 창은 켜둔 채로 두세요. (닫으면 종료)
echo ============================================
echo.

REM 가상환경 활성화
if not exist ".venv\Scripts\activate.bat" (
    echo [오류] .venv 가상환경이 없습니다.
    echo 최초 1회 설치가 필요합니다. README의 설치 안내를 참고하세요.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"

REM 잠시 후 브라우저 자동 열기 (서버가 뜰 시간 확보)
start "" /b cmd /c "timeout /t 3 >nul & start http://localhost:8501"

REM Streamlit 실행
streamlit run core\app.py

REM 서버 종료 시
echo.
echo 프로그램이 종료되었습니다.
pause
