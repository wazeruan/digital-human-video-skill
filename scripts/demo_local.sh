#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 AVATAR_IMAGE [TEXT]"
  exit 2
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_PATH="$1"
TEXT_VALUE="${2:-欢迎来到我的频道}"
API_PORT="${DIGITAL_HUMAN_API_PORT:-8000}"
SIDECAR_PORT="${DIGITAL_HUMAN_MUSETALK_PORT:-8001}"
MOTION_BACKEND="${DIGITAL_HUMAN_MOTION_BACKEND:-static}"
RENDER_MODE="${DIGITAL_HUMAN_RENDER_MODE:-musetalk}"
SIDE_PID=""
API_PID=""

cleanup() {
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$SIDE_PID" ]] && kill "$SIDE_PID" 2>/dev/null || true
}
trap cleanup EXIT

if [[ "$RENDER_MODE" == "musetalk" ]]; then
if ! curl -fsS "http://127.0.0.1:$SIDECAR_PORT/health" >/dev/null 2>&1; then
  (
    cd "$PROJECT_DIR/vendor/musetalk-mac"
    PORT="$SIDECAR_PORT" MUSETALK_BATCH_SIZE=4 ./run_server.sh
  ) > /tmp/digital-human-musetalk.log 2>&1 &
  SIDE_PID=$!
fi

for _ in {1..180}; do
  curl -fsS "http://127.0.0.1:$SIDECAR_PORT/health" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "http://127.0.0.1:$SIDECAR_PORT/health" >/dev/null
fi

cd "$PROJECT_DIR"
DIGITAL_HUMAN_BACKEND=local \
DIGITAL_HUMAN_RENDER_MODE="$RENDER_MODE" \
DIGITAL_HUMAN_MOTION_BACKEND="$MOTION_BACKEND" \
DIGITAL_HUMAN_DATA_DIR="$PROJECT_DIR/data-real" \
DIGITAL_HUMAN_MUSETALK_URL="http://127.0.0.1:$SIDECAR_PORT" \
HF_HUB_DISABLE_XET=1 \
  uv run uvicorn digital_human.api:app --host 127.0.0.1 --port "$API_PORT" \
  > /tmp/digital-human-api.log 2>&1 &
API_PID=$!

for _ in {1..60}; do
  kill -0 "$API_PID" 2>/dev/null || { tail -50 /tmp/digital-human-api.log; exit 1; }
  curl -fsS "http://127.0.0.1:$API_PORT/readyz" | /usr/bin/python3 -c \
    'import json,sys; sys.exit(0 if json.load(sys.stdin).get("ready") else 1)' 2>/dev/null && break
  sleep 0.5
done
curl -fsS "http://127.0.0.1:$API_PORT/readyz" | /usr/bin/python3 -c \
  'import json,sys; sys.exit(0 if json.load(sys.stdin).get("ready") else 1)'

AVATAR_ID="$(curl -fsS -X POST "http://127.0.0.1:$API_PORT/v1/avatars" \
  -F "image=@$IMAGE_PATH" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["avatar_id"])')"
REQUEST_JSON="$(AVATAR_ID="$AVATAR_ID" TEXT_VALUE="$TEXT_VALUE" /usr/bin/python3 -c \
  'import json,os; print(json.dumps({"avatar_id":os.environ["AVATAR_ID"],"text":os.environ["TEXT_VALUE"],"voice":"Vivian","language":"Chinese"}, ensure_ascii=False))')"
REQUEST_KEY="$(printf '%s' "$REQUEST_JSON" | shasum -a 256 | cut -d ' ' -f 1)"
JOB_ID="$(curl -fsS -X POST "http://127.0.0.1:$API_PORT/v1/renders" \
  -H 'Content-Type: application/json' -H "Idempotency-Key: real-demo-$REQUEST_KEY" \
  -d "$REQUEST_JSON" | \
  /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')"

for _ in {1..900}; do
  JOB_JSON="$(curl -fsS "http://127.0.0.1:$API_PORT/v1/jobs/$JOB_ID")"
  STATUS="$(printf '%s' "$JOB_JSON" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  [[ "$STATUS" == "succeeded" ]] && break
  if [[ "$STATUS" == "failed" ]]; then
    printf '%s\n' "$JOB_JSON"
    tail -100 /tmp/digital-human-api.log
    [[ "$RENDER_MODE" != "musetalk" ]] || tail -100 /tmp/digital-human-musetalk.log
    exit 1
  fi
  sleep 2
done

mkdir -p "$PROJECT_DIR/outputs"
curl -fsS "http://127.0.0.1:$API_PORT/v1/jobs/$JOB_ID/result" \
  -o "$PROJECT_DIR/outputs/final-local.mp4"
echo "$PROJECT_DIR/outputs/final-local.mp4"
