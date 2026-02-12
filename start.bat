@echo off
echo Starting ReelScript...
echo.

:: Start backend
echo [1/3] Starting backend (port 8002)...
start "ReelScript Backend" cmd /k "cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload"

:: Wait a moment for backend to start
timeout /t 2 /nobreak >nul

:: Start frontend
echo [2/3] Starting frontend (port 5173)...
start "ReelScript Frontend" cmd /k "cd frontend && npm run dev"

:: Start Telegram bot (if .env exists with token)
if exist "backend\.env" (
    echo [3/3] Starting Telegram bot...
    start "ReelScript TG Bot" cmd /k "cd backend && python -m services.telegram_bot"
) else (
    echo [3/3] Telegram bot skipped (no backend\.env found)
)

echo.
echo ReelScript is running!
echo   Backend:  http://localhost:8002
echo   Frontend: http://localhost:5173
echo   TG Bot:   check Telegram
echo.
pause
