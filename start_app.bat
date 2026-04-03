@echo off
echo Starting Mini RAG App...

start "Backend Server" cmd /k "cd backend && python main.py"
start "Frontend Server" cmd /k "cd frontend && npm run dev"

echo Servers started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
pause
