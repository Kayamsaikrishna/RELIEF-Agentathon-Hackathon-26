#!/usr/bin/env bash
# macOS / Linux: build the web app if needed and start RELIEF on http://127.0.0.1:8000
set -e
cd "$(dirname "$0")"
if [ ! -f frontend/dist/index.html ]; then (cd frontend && npm install && npm run build); fi
exec python -m uvicorn relief.app.api:create_app --factory --host 127.0.0.1 --port 8000
