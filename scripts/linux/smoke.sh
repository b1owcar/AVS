#!/usr/bin/env bash
# Phase 7 — Linux smoke (logic / API). Does NOT claim Windows GPU results transfer.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

API="${LAVS_SMOKE_API:-http://127.0.0.1:18765}"
FAIL=0

echo "== LAVS Linux smoke against $API =="
echo "Grade: Linux API/logic PASS ≠ Windows GPU PASS"

check() {
  local name="$1"
  local url="$2"
  local expect="$3"
  local body
  body="$(curl -fsS "$url" || true)"
  if [[ -z "$body" ]]; then
    echo "FAIL $name — empty/unreachable"
    FAIL=1
    return
  fi
  if echo "$body" | grep -q "$expect"; then
    echo "PASS $name"
  else
    echo "FAIL $name — expected /$expect/ in: $body"
    FAIL=1
  fi
}

check health "$API/api/health" '"ok":true'
check features "$API/api/features" 'video_studio'
check models "$API/api/models" 'mock-demo'
check video_status "$API/api/video/status" 'ffmpeg_available'
check motion_status "$API/api/motion/status" 'pose_extract'
check studio3d_status "$API/api/studio3d/status" 'image_to_3d'

# Mock task end-to-end
TASK="$(curl -fsS -X POST "$API/api/tasks" \
  -H 'Content-Type: application/json' \
  -d '{"task_type":"text_to_image","model_id":"mock-demo","parameters":{"prompt":"smoke","width":256,"height":256}}')"
TID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["task_id"])' <<<"$TASK")"
echo "mock task $TID"
STATUS="pending"
for _ in $(seq 1 40); do
  STATUS="$(curl -fsS "$API/api/tasks/$TID" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" || "$STATUS" == "cancelled" ]]; then
    break
  fi
  sleep 0.2
done
if [[ "$STATUS" == "completed" ]]; then
  echo "PASS mock_task"
else
  echo "FAIL mock_task status=$STATUS"
  FAIL=1
fi

# Real adapters must not fake-succeed without envs
SDXL="$(curl -fsS -X POST "$API/api/tasks" \
  -H 'Content-Type: application/json' \
  -d '{"task_type":"text_to_image","model_id":"sdxl-base-1.0","parameters":{"prompt":"x"}}')"
SID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["task_id"])' <<<"$SDXL")"
for _ in $(seq 1 40); do
  SSTATUS="$(curl -fsS "$API/api/tasks/$SID" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  [[ "$SSTATUS" == "completed" || "$SSTATUS" == "failed" || "$SSTATUS" == "cancelled" ]] && break
  sleep 0.1
done
if [[ "$SSTATUS" == "failed" ]]; then
  echo "PASS sdxl_not_ready_fails_honestly"
else
  echo "FAIL sdxl_not_ready_fails_honestly status=$SSTATUS"
  FAIL=1
fi

echo "----"
if [[ "$FAIL" -eq 0 ]]; then
  echo "SMOKE PASS (Linux logic). Hardware/GPU grades remain separate."
  exit 0
fi
echo "SMOKE FAIL"
exit 1
