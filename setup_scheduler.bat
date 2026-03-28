@echo off
:: ============================================================
:: SCOUTE — Windows Task Scheduler setup
:: Run this file as Administrator (right-click > Run as administrator)
:: ============================================================

set TASK_NAME=SCOUTE Daily Pipeline
set BAT_FILE=C:\Users\akash\Desktop\scoute\run_pipeline.bat
set RUN_TIME=09:00

echo.
echo  SCOUTE Task Scheduler Setup
echo  ============================
echo.

:: Check for admin rights
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  ERROR: This script must be run as Administrator.
    echo  Right-click setup_scheduler.bat and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)

:: Delete existing task if it exists (allows re-running this script safely)
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo  Removing existing task: "%TASK_NAME%"...
    schtasks /delete /tn "%TASK_NAME%" /f >nul
)

:: Create the task
:: /sc DAILY         — run every day
:: /st 09:00         — at 9:00 AM
:: /ru SYSTEM        — run as SYSTEM (no login required)
:: /rl HIGHEST       — run with highest privileges
:: /f                — force creation, overwrite if exists
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "cmd /c \"%BAT_FILE%\"" ^
    /sc DAILY ^
    /st %RUN_TIME% ^
    /ru SYSTEM ^
    /rl HIGHEST ^
    /f

if %ERRORLEVEL% == 0 (
    echo.
    echo  SUCCESS: Task created.
    echo.
    echo  Task name : %TASK_NAME%
    echo  Runs      : Every day at %RUN_TIME%
    echo  Script    : %BAT_FILE%
    echo  Log file  : C:\Users\akash\Desktop\scoute\logs\pipeline_log.txt
    echo  Account   : SYSTEM (runs even when you are logged out)
    echo.
    echo  To verify, open Task Scheduler and look for "%TASK_NAME%".
    echo  To run it now manually:
    echo      schtasks /run /tn "%TASK_NAME%"
    echo.
    echo  To remove it later:
    echo      schtasks /delete /tn "%TASK_NAME%" /f
    echo.
) else (
    echo.
    echo  ERROR: Task creation failed. Exit code: %ERRORLEVEL%
    echo  Make sure you right-clicked and chose "Run as administrator".
    echo.
)

pause
