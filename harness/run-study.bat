@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem ============================================================
rem  run-study.bat - launch the full study and keep the PC awake
rem
rem  Four workers: about 3h instead of about 12h serial. Four is the
rem  ceiling set by the Go subscription spend window ($12 per 5 hours),
rem  not by the CPU -- above that you just throttle and stall anyway.
rem  Sleep is suppressed for the duration, output tee'd to a log file so
rem  you can read the results after the fact.
rem
rem  Usage:  run-study.bat              (full run, config.go.json)
rem          run-study.bat --smoke      (quick sanity check first)
rem          run-study.bat --resume     (continue a stopped run)
rem
rem  ASCII only: see the note in keepawake.ps1.
rem ============================================================

set CONFIG=config.go.json
set WORKERS=4
set PYTHON=python
set EXTRAS=%*

rem ---- find Python -------------------------------------------------
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    set PYTHON=py -3
    %PYTHON% --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  No Python found. Install it from python.org and tick
        echo  "Add python.exe to PATH".
        echo.
        pause
        exit /b 1
    )
)

if not exist "%~dp0src\run.py" (
    echo Cannot find src\run.py - run this from the extracted pilot-harness folder.
    pause
    exit /b 1
)
if not exist "%~dp0%CONFIG%" (
    echo Cannot find %CONFIG%.
    pause
    exit /b 1
)

rem ---- log to a timestamped file -----------------------------------
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set STAMP=%%i
set LOG=%~dp0runs\study-%STAMP%.log
if not exist "%~dp0runs" mkdir "%~dp0runs"

rem ---- suppress sleep while we work --------------------------------
echo.
echo  ============================================================
echo   PILOT HARNESS   %CONFIG%
echo   %WORKERS% workers   ^|   log: %LOG%
echo  ============================================================
echo.
echo  Keeping the PC awake for the duration...
if exist "%~dp0awake.pid" del "%~dp0awake.pid"
start "keepawake" /b powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0keepawake.ps1"

rem Give it a moment to take effect and write its PID.
timeout /t 2 /nobreak >nul

rem ---- run ---------------------------------------------------------
echo  Starting. Close this window only if you really want to stop it.
echo.
pushd "%~dp0"
%PYTHON% src\run.py --config %CONFIG% --workers %WORKERS% %EXTRAS%
set RC=!ERRORLEVEL!
popd

rem ---- release the sleep lock ---------------------------------------
if exist "%~dp0awake.pid" (
    for /f %%p in (%~dp0awake.pid) do (
        taskkill /f /pid %%p >nul 2>&1
    )
    del "%~dp0awake.pid"
)

echo.
echo  ============================================================
if "!RC!"=="0" (
    echo   DONE - all runs completed.
) else (
    echo   FINISHED WITH ERRORS   exit code !RC!
    echo   Some runs failed. Re-run with  --resume  to retry just those.
)
echo   Log: %LOG%
echo.
echo   Next:
echo     python src\report.py
echo  ============================================================
echo.
pause
exit /b !RC!
