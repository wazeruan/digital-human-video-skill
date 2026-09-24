#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 AVATAR_IMAGE [TEXT]"
  exit 2
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_PATH="$1"
TEXT_VALUE="${2:-欢迎来到我的频道}"
PORT="${DIGITAL_HUMAN_DEMO_PORT:-8010}"
DATA_DIR="$PROJECT_DIR/data-demo"

cd "$PROJECT_DIR"
DIGITAL_HUMAN_BACKEND=fake DIGITAL_HUMAN_DATA_DIR="$DATA_DIR" \
  uv run uvicorn digital_human.api:app --host 127.0.0.1 --port "$PORT" >/tmp/digital-human-demo.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

for _ in {1..40}; do
  if curl -fsS "http://127.0.0.1:$PORT/readyz" >/dev/null; then break; fi
  sleep 0.25
done

AVATAR_ID="$(curl -fsS -X POST "http://127.0.0.1:$PORT/v1/avatars" -F "image=@$IMAGE_PATH" | \
  /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["avatar_id"])')"
JOB_ID="$(curl -fsS -X POST "http://127.0.0.1:$PORT/v1/renders" \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: local-demo-v1' \
  -d "{\"avatar_id\":\"$AVATAR_ID\",\"text\":\"$TEXT_VALUE\"}" | \
  /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')"

for _ in {1..120}; do
  STATUS="$(curl -fsS "http://127.0.0.1:$PORT/v1/jobs/$JOB_ID" | \
    /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  [[ "$STATUS" == "succeeded" ]] && break
  [[ "$STATUS" == "failed" ]] && { cat /tmp/digital-human-demo.log; exit 1; }
  sleep 0.25
done

mkdir -p "$PROJECT_DIR/outputs"
curl -fsS "http://127.0.0.1:$PORT/v1/jobs/$JOB_ID/result" -o "$PROJECT_DIR/outputs/demo.mp4"
echo "$PROJECT_DIR/outputs/demo.mp4"
