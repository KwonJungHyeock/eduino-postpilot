@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Eduino PostPilot - 바탕화면 바로가기 만들기

set "TARGET=%~dp0dist\EduinoPostPilot\EduinoPostPilot.exe"
set "WORKDIR=%~dp0dist\EduinoPostPilot"

if not exist "%TARGET%" (
    echo [오류] 빌드된 실행파일이 없습니다:
    echo        %TARGET%
    echo        먼저 build_exe.bat 으로 빌드하세요.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$lnk = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Eduino PostPilot.lnk');" ^
  "$lnk.TargetPath = '%TARGET%';" ^
  "$lnk.WorkingDirectory = '%WORKDIR%';" ^
  "$lnk.IconLocation = '%TARGET%,0';" ^
  "$lnk.Description = 'Eduino PostPilot - 블로그 초안 자동 생성';" ^
  "$lnk.Save()"

echo.
echo 바탕화면에 'Eduino PostPilot' 아이콘을 만들었습니다. 더블클릭으로 실행하세요.
echo.
pause
