@echo off
title RooftopGreen AI - Project Launcher
echo ========================================================
echo           Starting RooftopGreen AI Platform
echo ========================================================

REM Add Node.js and Python to PATH in case they are not in global system PATH
set "PATH=C:\Program Files\nodejs;%LOCALAPPDATA%\Python\bin;%LOCALAPPDATA%\Python\pythoncore-3.15-64;%LOCALAPPDATA%\Python\pythoncore-3.15-64\Scripts;%PATH%"

set "PROJECT_ROOT=%~dp0"

echo [1/2] Launching FastAPI Backend on http://localhost:8000...
start "RooftopGreen Backend (FastAPI)" cmd /k "cd /d "%PROJECT_ROOT%backend" && (py run.py || python run.py || py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload || python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload)"

timeout /t 3 /nobreak >nul

echo [2/2] Launching Vite React Frontend on http://localhost:5173...
start "RooftopGreen Frontend (Vite)" cmd /k "cd /d "%PROJECT_ROOT%RoofTop-AI-main" && npm run dev"

echo ========================================================
echo  Both services launched in separate windows!
echo  - Frontend UI : http://localhost:5173
echo  - Backend API : http://localhost:8000
echo  - API Docs    : http://localhost:8000/docs
echo ========================================================
