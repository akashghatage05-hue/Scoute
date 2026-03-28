@echo off
setlocal enabledelayedexpansion

set PROJECT_DIR=C:\Users\akash\Desktop\scoute
set LOG_FILE=%PROJECT_DIR%\logs\pipeline_log.txt

:: Change to project directory
cd /d "%PROJECT_DIR%"

:: Create logs dir if it doesn't exist
if not exist logs mkdir logs

:: Build timestamp from wmic
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list 2^>nul') do set DT=%%I
set TIMESTAMP=%DT:~0,4%-%DT:~4,2%-%DT:~6,2% %DT:~8,2%:%DT:~10,2%:%DT:~12,2%

echo. >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"
echo [%TIMESTAMP%] SCOUTE pipeline started >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

:: Activate virtual environment if one exists in the project
if exist "%PROJECT_DIR%\venv\Scripts\activate.bat" (
    echo [%TIMESTAMP%] Activating venv... >> "%LOG_FILE%"
    call "%PROJECT_DIR%\venv\Scripts\activate.bat"
)

:: Run the full pipeline and append all output to the log
echo [%TIMESTAMP%] Running: python main.py >> "%LOG_FILE%"
python main.py >> "%LOG_FILE%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

echo [%TIMESTAMP%] Pipeline finished. Exit code: %EXIT_CODE% >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"

endlocal
exit /b %EXIT_CODE%
