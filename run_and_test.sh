#!/bin/bash
# Start backend and frontend, then run a quick API test.
# Usage: ./run_and_test.sh
# Use LLM_PROVIDER=mock for key-free testing, or set GOOGLE_API_KEY in .env for Gemini.

set -e
cd "$(dirname "$0")"

echo "Starting backend (port 8000)..."
LLM_PROVIDER="${LLM_PROVIDER:-gemini}" venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 3

echo "Testing /api/analyze..."
RESP=$(curl -s -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"tab_switch_count": 1, "keystroke_count": 8, "total_events": 20, "session_duration_seconds": 45.0}')
if echo "$RESP" | grep -q '"insight"' && echo "$RESP" | grep -q '"verification_certificate"'; then
  echo "  OK: API returned insight + verification_certificate"
else
  echo "  FAIL: $RESP"
  kill $BACKEND_PID 2>/dev/null || true
  exit 1
fi

echo "Starting frontend (port 8080)..."
python3 -m http.server 8080 &
FRONT_PID=$!
sleep 1
echo ""
echo "Backend:  http://127.0.0.1:8000  (docs: http://127.0.0.1:8000/docs)"
echo "Frontend: http://127.0.0.1:8080/demo.html"
echo ""
echo "Press Ctrl+C to stop both."
trap "kill $BACKEND_PID $FRONT_PID 2>/dev/null; exit 0" INT TERM
wait
