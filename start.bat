@echo off
echo Starting ReelScript...
echo.

:: Start backend
echo [1/2] Starting backend (port 8002)...
start "ReelScript Backend" cmd /k "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload"

:: Wait a moment for backend to start
timeout /t 2 /nobreak >nul

:: Start frontend
echo [2/2] Starting frontend (port 5173)...
start "ReelScript Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ReelScript is running!
echo   Backend:  http://localhost:8002
echo   Frontend: http://localhost:5173
echo.
pause
