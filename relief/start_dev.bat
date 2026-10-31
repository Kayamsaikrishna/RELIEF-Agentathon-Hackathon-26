@echo off
title RELIEF - Vite Frontend Dev Server
echo =====================================================================
echo  RELIEF: Vite Frontend Dev Server (Hot Module Reloading)
echo  http://localhost:5173
echo =====================================================================
cd /d "%~dp0frontend"
npm run dev
pause

