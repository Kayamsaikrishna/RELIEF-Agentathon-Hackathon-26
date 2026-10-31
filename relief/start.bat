@echo off
title RELIEF - Local Agent & Web App
echo =====================================================================
echo  RELIEF: Find the block. Clear the way.
echo  Starting on http://127.0.0.1:8000
echo =====================================================================
cd /d "%~dp0"
set PYTHONPATH=%~dp0src;%PYTHONPATH%

if not exist frontend\dist\index.html (
  echo Building the web app...
  pushd frontend
  call npm install
  call npm run build
  popd
)

set PY_EXE=python
if exist "C:\Users\ASUS\.conda\envs\relief\python.exe" (
  set PY_EXE="C:\Users\ASUS\.conda\envs\relief\python.exe"
)

%PY_EXE% -m uvicorn relief.app.api:create_app --factory --host 127.0.0.1 --port 8000 --reload
pause
