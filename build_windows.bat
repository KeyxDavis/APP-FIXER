@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH.
    exit /b 1
)

python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo PyInstaller is not installed.
    echo Install it with: python -m pip install pyinstaller
    exit /b 1
)

echo Building AsoloAttendance.exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed --log-level WARN --name AsoloAttendance --exclude-module pygments --exclude-module IPython --exclude-module pytest --exclude-module notebook --exclude-module setuptools --exclude-module pkg_resources "STAFF ATTENDANCE(GENERAL)KIVY.py"
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

if exist "asolo_config.json" copy /Y "asolo_config.json" "dist\asolo_config.json" >nul

echo.
echo Build complete:
dist\AsoloAttendance.exe
if not exist "asolo_config.json" echo Add asolo_config.json beside the exe before sharing it.
endlocal
