@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Build EduinoPostPilot.exe

echo ============================================
echo   Eduino PostPilot - 실행파일(.exe) 빌드
echo ============================================
echo   이 작업은 5~10분 정도 걸립니다.
echo   인터넷 연결이 필요합니다.
echo.

REM --- Python 확인 ---
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
    echo [오류] Python이 설치되어 있지 않습니다. https://www.python.org/downloads/ 에서 설치하세요.
    echo        ("Add Python to PATH" 체크 필수^)
    pause & exit /b 1
)

REM --- 빌드 전용 가상환경 ---
if not exist ".venv_build\Scripts\activate.bat" (
    echo [1/3] 빌드용 가상환경 생성...
    %PY% -m venv .venv_build
)
call ".venv_build\Scripts\activate.bat"

echo [2/3] 의존성 + PyInstaller 설치...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt pyinstaller
if errorlevel 1 ( echo [오류] 설치 실패. 인터넷 연결 확인 후 다시 실행하세요. & pause & exit /b 1 )

echo [3/3] 실행파일 빌드 (PyInstaller)...
pyinstaller --noconfirm --clean EduinoPostPilot.spec
if errorlevel 1 ( echo [오류] 빌드 실패. 위 로그를 확인하세요. & pause & exit /b 1 )

echo.
echo ============================================
echo   빌드 완료!
echo.
echo   배포물:  dist\EduinoPostPilot\  폴더 전체
echo   - 이 폴더를 통째로 압축(zip)해서 동료에게 전달하세요.
echo   - 동료는 압축을 풀고  EduinoPostPilot.exe  를 더블클릭하면 됩니다.
echo   - Python 설치 불필요. 최초 실행 시 화면에서 OpenAI 키만 한 번 입력.
echo ============================================
echo.
pause
