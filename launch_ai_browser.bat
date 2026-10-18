@echo off
setlocal

echo ========================================================
echo Launching Chrome with CDP Remote Debugging on Port 9222
echo Dedicated Profile: %LOCALAPPDATA%\Google\Chrome\AIBridgeProfile
echo Opening: Gemini Web and ChatGPT Web
echo ========================================================

set "CHROME_PATH="

if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
) else if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) else (
    where chrome >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        for /f "tokens=*" %%i in ('where chrome') do (
            set "CHROME_PATH=%%i"
            goto :found
        )
    )
)

:found
if "%CHROME_PATH%"=="" (
    echo [ERROR] Google Chrome was not found in standard directories or PATH.
    echo Please install Google Chrome or update the CHROME_PATH variable in this script.
    pause
    exit /b 1
)

echo Found Chrome at: "%CHROME_PATH%"
echo Starting browser instance...

start "" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\AIBridgeProfile" --profile-directory="Default" --no-first-run --no-default-browser-check --disable-extensions --disable-features=WebUIOmniboxPopup "https://gemini.google.com/app" "https://chatgpt.com"

echo.
echo Browser launched! Once you log in, Antigravity and web_ai_bridge_mcp.py can control both tabs.
