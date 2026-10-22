@echo off
rem Starts the dashboard and logs everything to dashboard_startup.log.
rem Run at logon by the GradDashboardAutoStart task / Startup-folder script - see CLAUDE.md.
set "ROOT=C:\Users\ayaan\OneDrive\Claude\Grad and Internship Dashboard"
set "LOG=%ROOT%\dashboard_startup.log"

rem Roll the log once it passes ~1 MB so it can't grow forever.
if exist "%LOG%" for %%F in ("%LOG%") do if %%~zF GTR 1000000 move /y "%LOG%" "%LOG%.old" >nul 2>&1

echo ---- launch attempt %date% %time% ---- >> "%LOG%"

rem Already running (e.g. both logon mechanisms fired)? Then there is nothing to do.
netstat -ano | findstr /R /C:":5173 .*LISTENING" >nul && (echo already listening on 5173 - not starting a second copy>> "%LOG%" & exit /b 0)

rem Hardcoding Python312 broke on 2026-09-29 when 3.12 was replaced by 3.14. Instead take the
rem first installed Python that can import Flask, so the launcher survives upgrades.
set "PY="
for /f "delims=" %%D in ('dir /b /ad /o-n "%LOCALAPPDATA%\Programs\Python" 2^>nul') do if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\%%D\python.exe" "%LOCALAPPDATA%\Programs\Python\%%D\python.exe" -c "import flask" >nul 2>&1 && set "PY=%LOCALAPPDATA%\Programs\Python\%%D\python.exe"
if not defined PY (echo NO PYTHON WITH FLASK FOUND under %LOCALAPPDATA%\Programs\Python. A newly installed Python needs: python -m pip install -r requirements.txt>> "%LOG%" & exit /b 1)

echo using %PY%>> "%LOG%"
"%PY%" "%ROOT%\app.py" >> "%LOG%" 2>&1
