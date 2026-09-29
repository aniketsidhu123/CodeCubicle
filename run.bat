@echo off
echo =========================================
echo Starting Tracelight...
echo =========================================

echo Starting Backend...
start "Tracelight Backend" cmd /k "cd backend && call venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Frontend...
start "Tracelight Frontend" cmd /k "cd frontend && npm run dev"

echo =========================================
echo Servers have been launched in separate windows!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo =========================================
