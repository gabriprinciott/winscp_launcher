@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "RUNNER=%SCRIPT_DIR%runner.py"

rem ============================================================
rem Logging
rem ============================================================

set "LOG_DIR=%SCRIPT_DIR%logs"

if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%" 2>nul
)

for /f "tokens=1-4 delims=/:-. " %%a in ("%date% %time%") do (
    set "TS=%%d%%b%%c_%%e%%f%%g"
)

set "LOG_FILE=%LOG_DIR%\launcher.log"

call :LOG ============================================================
call :LOG START
call :LOG DATE=%date% TIME=%time%
call :LOG SCRIPT_DIR=%SCRIPT_DIR%
call :LOG RUNNER=%RUNNER%
call :LOG CD=%CD%
call :LOG USERNAME=%USERNAME%
call :LOG SESSIONNAME=%SESSIONNAME%
call :LOG ============================================================

rem ============================================================
rem .venv
rem ============================================================

call :LOG Checking .venv...

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    call :LOG FOUND .venv python
    set "PY_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
    goto :RUN
)

call :LOG .venv not found

if exist "%SCRIPT_DIR%venv\Scripts\python.exe" (
    call :LOG FOUND venv python
    set "PY_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"
    goto :RUN
)

call :LOG venv not found

rem ============================================================
rem py launcher
rem ============================================================

call :LOG Executing WHERE PY

where py >> "%LOG_FILE%" 2>&1

call :LOG WHERE PY RC=%ERRORLEVEL%

if %ERRORLEVEL% equ 0 (
    call :LOG Python launcher found
    set "PY_EXE=py -3"
    goto :RUN
)

rem ============================================================
rem python from PATH
rem ============================================================

call :LOG Executing WHERE PYTHON

where python >> "%LOG_FILE%" 2>&1

call :LOG WHERE PYTHON RC=%ERRORLEVEL%

if %ERRORLEVEL% equ 0 (
    call :LOG Python found in PATH
    set "PY_EXE=python"
    goto :RUN
)

rem ============================================================
rem Failure
rem ============================================================

call :LOG ERROR: Python not found
echo [ERROR] Python not found
pause

exit /b 1

rem ============================================================
rem Run
rem ============================================================

:RUN

call :LOG ============================================================
call :LOG ENTERING RUN
call :LOG PY_EXE=%PY_EXE%
call :LOG RUNNER=%RUNNER%
call :LOG ============================================================

if not exist "%RUNNER%" (
    call :LOG ERROR: runner.py NOT FOUND
    exit /b 2
)

call :LOG Launching python...

%PY_EXE% "%RUNNER%" %* >> "%LOG_FILE%" 2>&1

set "RC=%ERRORLEVEL%"

call :LOG Python finished RC=%RC%

exit /b %RC%

rem ============================================================
rem Logger
rem ============================================================

:LOG
echo [%date% %time%] %*>>"%LOG_FILE%"
goto :eof