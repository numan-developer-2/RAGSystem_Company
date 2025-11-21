@echo off
echo ========================================
echo UniSoftware Assistant - System Startup
echo ========================================
echo.

REM Change to project directory
cd /d "D:\Python Project\RAG Project\rag-openrouter"

echo [1/3] Checking if port 8000 is free...
netstat -ano | findstr :8000 > nul
if %errorlevel% equ 0 (
    echo Port 8000 is in use. Killing existing process...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
        taskkill /F /PID %%a > nul 2>&1
    )
    timeout /t 2 > nul
)
echo Port 8000 is free!
echo.

echo [2/3] Starting Backend API Server...
start "RAG Backend API" cmd /k "cd /d D:\Python Project\RAG Project\rag-openrouter && python src/api_openrouter.py"
echo Waiting for backend to initialize (15 seconds)...
timeout /t 15 > nul
echo.

echo [3/3] Starting Frontend Streamlit...
start "RAG Frontend UI" cmd /k "cd /d D:\Python Project\RAG Project\rag-openrouter && streamlit run src/frontend_streamlit.py"
echo Waiting for frontend to start (8 seconds)...
timeout /t 8 > nul
echo.

echo ========================================
echo System Started Successfully!
echo ========================================
echo.
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:8501
echo.
echo Press any key to open browser...
pause > nul

start http://localhost:8501

echo.
echo System is running in separate windows.
echo Close those windows to stop the system.
echo.
pause
