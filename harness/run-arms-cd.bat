@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem ============================================================
rem  run-arms-cd.bat - the two NEW arms only
rem
rem    C  full specification   the user spells out every want
rem    D  plan-then-correct    the model plans, the user corrects
rem                             the plan, then it implements
rem
rem  Default scope: the two new real-world agentic items.
rem     T11 (customer refund over the policy limit)
rem     T13 (night incident from the logs)
rem
rem  48 runs = 6 models x 2 arms x 2 reps x 2 items
rem  Four workers. Sleep suppressed, output tee'd to a log.
rem
rem  Usage:
rem    run-arms-cd.bat                    T11+T13, arms C+D  (48 runs)
rem    run-arms-cd.bat --items T11        just the refund item
rem    run-arms-cd.bat --items T11,T13,T6 all agentic items
rem    run-arms-cd.bat --items T1,T2,T3,T4,T5,T6,T7,T8,T9,T11,T13
rem                                       every item, arms C+D (264 runs)
rem    run-arms-cd.bat --smoke            quick sanity check first
rem
rem  Extra args are appended after --arms, so --items overrides the
rem  default scope and --models narrows the model set.
rem ============================================================

set CONFIG=config.go.json
set WORKERS=4
set PYTHON=python
set ITEMS=T11,T13
set ARMS=C,D

rem ---- find Python -------------------------------------------------
where %PYTHON% >nul 2>&1 || set PYTHON=py

rem ---- keep the PC awake -------------------------------------------
if exist "%~dp0awake.pid" del "%~dp0awake.pid"
start "keepawake" /b powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0keepawake.ps1"

set LOG=%~dp0runs\arms-cd.log
if not exist "%~dp0runs" mkdir "%~dp0runs"

echo ============================================================
echo   Arms C and D only
echo     C  full specification
echo     D  plan first, user corrects the plan
echo   Items: %ITEMS%
echo   %WORKERS% workers   ^|   log: %LOG%
echo   Keep this window open. Your PC will not sleep until it closes.
echo ============================================================

%PYTHON% src\run.py --config %CONFIG% --workers %WORKERS% --arms %ARMS% --items %ITEMS% %*
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
