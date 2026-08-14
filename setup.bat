@echo off
setlocal

echo Checking for Python...
where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo Python was not found on PATH.
    echo Install it from https://www.python.org/downloads/ ^(check "Add python.exe to PATH"^) and re-run this script.
    pause
    exit /b 1
)

python --version

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing dependencies from requirements.txt...
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo Installation failed. See the error above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete.
echo.
echo  Run the app with:
echo      python "%~dp0run.py"
echo.
echo  Note: translating a screenshot (OCR) needs a Windows OCR
echo  language pack. If it doesn't work, add one under
echo  Settings ^> Time ^& language ^> Language ^& region, then
echo  enable "Optical character recognition" for that language.
echo ============================================================
pause
