@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Eduino PostPilot

echo ============================================
echo   Eduino PostPilot
echo ============================================
echo.

REM --- Python 확인 (py 런처 우선, 없으면 python) ---
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo        https://www.python.org/downloads/ 에서 설치 후 다시 실행하세요.
    echo        설치 화면에서 "Add Python to PATH" 를 꼭 체크하세요.
    echo.
    pause
    exit /b 1
)

REM --- 최초 1회: 가상환경 생성 + 패키지 자동 설치 ---
if not exist ".venv\Scripts\activate.bat" (
    echo [최초 설정] 실행 환경을 준비합니다... 1~3분 정도 걸립니다.
    echo.
    %PY% -m venv .venv
    if errorlevel 1 ( echo [오류] 가상환경 생성 실패. & pause & exit /b 1 )
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip >nul 2>nul
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [오류] 패키지 설치 실패. 인터넷 연결을 확인하고 다시 실행하세요.
        pause
        exit /b 1
    )
    echo.
    echo [설정 완료]
) else (
    call ".venv\Scripts\activate.bat"
)

echo.
echo   준비 완료! 잠시 후 브라우저가 자동으로 열립니다.
echo   안 열리면 브라우저에서  localhost:8501  로 접속하세요.
echo   처음 실행이면 화면에서 OpenAI 키를 한 번만 입력하면 됩니다.
echo   (키는 이 PC에만 저장되어 다음부터 자동 적용됩니다)
echo.
echo   이 검은 창은 닫지 마세요. 닫으면 프로그램이 종료됩니다.
echo.

streamlit run core\app.py

echo.
echo App stopped.
pause
