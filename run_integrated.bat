@echo off
echo ===================================================
echo   Building and Starting Integrated Mini RAG App
echo ===================================================

echo [1/2] Building Frontend...
cd frontend
call npm install
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo Frontend build failed!
    pause
    exit /b %ERRORLEVEL%
)
cd ..

echo [2/2] Starting Backend (Serving Frontend)...
cd backend
echo Server running at http://localhost:8000
python main.py

pause
