@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem ============================================================
rem  run-new-agentic.bat - run ONLY the two new real-world agentic
rem  items (T11 refund, T13 incident). Same 6 models, 3 arms, 2 reps.
rem
rem  72 runs: 6 models x 3 arms x 2 reps x 2 items
rem  Four workers. Sleep suppressed for the duration, output tee'd
rem  to a log file so you can read the results after.
rem
rem  Usage:  run-new-agentic.bat              (the 72 runs)
rem          run-new-agentic.bat --smoke      (quick sanity check first)
rem ============================================================

set CONFIG=config.go.json
set WORKERS=4
set PYTHON=python
set EXTRAS=%*

rem ---- find Python -------------------------------------------------
where %PYTHON% >nul 2>&1 || set PYTHON=py

rem ---- keep the PC awake -------------------------------------------
if exist "%~dp0awake.pid" del "%~dp0awake.pid"
start "keepawake" /b powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0keepawake.ps1"

set LOG=%~dp0runs\new-agentic.log
if not exist "%~dp0runs" mkdir "%~dp0runs"

echo ============================================================
echo   New real-world agentic items: T11 (refund) + T13 (incident)
echo   %WORKERS% workers   ^|   log: %LOG%
echo   Keep this window open. Your PC will not sleep until it closes.
echo ============================================================

%PYTHON% src\run.py --config %CONFIG% --workers %WORKERS% --items T11,T13 %EXTRAS%
set RC=!ERRORLEVEL!

echo.
echo   exit code: %RC%
echo   results:   %~dp0runs\

if exist "%~dp0awake.pid" (
    for /f %%p in (%~dp0awake.pid) do (
        powershell -NoProfile -Command "Stop-Process -Id %%p -Force" >nul 2>&1
    )
    del "%~dp0awake.pid"
)

echo   Sleep lock released. You can close this window.
exit /b %RC%
