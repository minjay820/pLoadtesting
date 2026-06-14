#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/target-apps/docker-compose.target-apps.yml"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ploadtesting-target-apps-smoke}"
HEALTH_RETRIES="${HEALTH_RETRIES:-30}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"
CURL_MAX_TIME_SECONDS="${CURL_MAX_TIME_SECONDS:-10}"
BUILD_TIMEOUT_SECONDS="${BUILD_TIMEOUT_SECONDS:-300}"
UP_TIMEOUT_SECONDS="${UP_TIMEOUT_SECONDS:-180}"

SERVICES=(
  "echo-api|http://127.0.0.1:18080/health|GET|http://127.0.0.1:18080/api/echo?message=smoke&repeat=1|"
  "latency-api|http://127.0.0.1:18081/health|GET|http://127.0.0.1:18081/api/delay/25|"
  "error-api|http://127.0.0.1:18082/health|GET|http://127.0.0.1:18082/api/flaky?rate=0&deterministic=true&request_key=smoke|"
  "resource-api|http://127.0.0.1:18083/health|GET|http://127.0.0.1:18083/api/cpu?iterations=1000|"
  "payload-api|http://127.0.0.1:18084/health|FILE|payload-api|"
  "crud-api|http://127.0.0.1:18085/health|GET|http://127.0.0.1:18085/api/items|"
  "auth-flow-api|http://127.0.0.1:18086/health|AUTH|auth-flow-api|"
  "sse-api|http://127.0.0.1:18087/health|GET|http://127.0.0.1:18087/api/events?count=2&interval_ms=1|"
  "ws-api|http://127.0.0.1:18088/health|WS|ws-api|"
  "db-api|http://127.0.0.1:18089/health|POST|http://127.0.0.1:18089/api/records|{\"name\":\"smoke-record\",\"category\":\"smoke\",\"value\":11,\"status\":\"ready\"}"
)

dump_diagnostics() {
  echo "== docker compose ps =="
  docker compose -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" ps || true
  echo "== docker compose logs =="
  docker compose -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" logs --no-color || true
}

cleanup() {
  docker compose -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" down --remove-orphans --volumes || true
}

trap cleanup EXIT
trap dump_diagnostics ERR

run_with_timeout() {
  local seconds="$1"
  shift
  python3 - "$seconds" "$@" <<'PY'
import subprocess
import sys

timeout_seconds = int(sys.argv[1])
cmd = sys.argv[2:]
completed = subprocess.run(cmd, timeout=timeout_seconds, check=False)
sys.exit(completed.returncode)
PY
}

retry_health() {
  local name="$1"
  local url="$2"

  for attempt in $(seq 1 "${HEALTH_RETRIES}"); do
    if curl -fsS --max-time "${CURL_MAX_TIME_SECONDS}" "${url}" >/dev/null 2>/dev/null; then
      echo "health ok: ${name}"
      return 0
    fi
    sleep "${HEALTH_SLEEP_SECONDS}"
  done

  echo "health failed after retries: ${name} ${url}" >&2
  return 1
}

call_representative() {
  local method="$1"
  local url="$2"
  local payload="$3"
  if [[ "${method}" == "FILE" ]]; then
    python3 - <<'PY'
import hashlib
import json
import urllib.request

manifest = urllib.request.urlopen("http://127.0.0.1:18084/api/files/manifest?count=2&kb_per_file=8", timeout=10)
manifest_payload = json.loads(manifest.read().decode("utf-8"))
assert manifest_payload["count"] == 2

download = urllib.request.urlopen("http://127.0.0.1:18084/api/files/fixture-1?kb=8", timeout=10)
body = download.read()
assert len(body) == 8 * 1024

request = urllib.request.Request(
    "http://127.0.0.1:18084/api/files/upload?filename=fixture-1.bin",
    data=body,
    headers={"Content-Type": "application/octet-stream"},
    method="POST",
)
upload = urllib.request.urlopen(request, timeout=10)
upload_payload = json.loads(upload.read().decode("utf-8"))
assert upload_payload["received_bytes"] == 8 * 1024
assert upload_payload["sha256_prefix"] == hashlib.sha256(body).hexdigest()[:16]
PY
    return 0
  fi
  if [[ "${method}" == "AUTH" ]]; then
    python3 - <<'PY'
import json
import urllib.error
import urllib.request

def post(url, payload, headers=None):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    return urllib.request.urlopen(request, timeout=10)

login = post(
    "http://127.0.0.1:18086/api/login",
    {"username": "smoke", "password": "demo-password", "access_token_uses": 1, "refresh_uses": 2},
)
login_payload = json.loads(login.read().decode("utf-8"))
access_token = login_payload["access_token"]
refresh_token = login_payload["refresh_token"]
auth_headers = {"Authorization": f"Bearer {access_token}"}

profile = urllib.request.urlopen(
    urllib.request.Request("http://127.0.0.1:18086/api/profile", headers=auth_headers),
    timeout=10,
)
assert profile.status == 200

try:
    urllib.request.urlopen(
        urllib.request.Request("http://127.0.0.1:18086/api/profile", headers=auth_headers),
        timeout=10,
    )
    raise AssertionError("expected expired bearer token")
except urllib.error.HTTPError as exc:
    assert exc.code == 401

refresh = post(
    "http://127.0.0.1:18086/api/refresh",
    {"refresh_token": refresh_token, "access_token_uses": 2},
)
refresh_payload = json.loads(refresh.read().decode("utf-8"))
refreshed_token = refresh_payload["access_token"]
refreshed_headers = {"Authorization": f"Bearer {refreshed_token}"}

logout = urllib.request.urlopen(
    urllib.request.Request("http://127.0.0.1:18086/api/logout", headers=refreshed_headers, method="POST"),
    timeout=10,
)
assert logout.status == 200
PY
    return 0
  fi
  if [[ "${method}" == "WS" ]]; then
    docker compose -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" exec -T "${url}" python - <<'PY'
import asyncio
import json

import websockets


async def main():
    async with websockets.connect("ws://127.0.0.1:8000/ws/echo?deterministic=true") as echo_ws:
        welcome = await asyncio.wait_for(echo_ws.recv(), timeout=3)
        welcome_payload = json.loads(welcome)
        assert welcome_payload["event"] == "welcome"
        await echo_ws.send("smoke-echo")
        echoed = await asyncio.wait_for(echo_ws.recv(), timeout=3)
        echoed_payload = json.loads(echoed)
        assert echoed_payload["event"] == "echo"
        assert echoed_payload["message"] == "smoke-echo"

    async with websockets.connect("ws://127.0.0.1:8000/ws/broadcast/smoke-room?client_id=subscriber&deterministic=true") as subscriber:
        subscriber_welcome = json.loads(await asyncio.wait_for(subscriber.recv(), timeout=3))
        assert subscriber_welcome["event"] == "welcome"
        async with websockets.connect("ws://127.0.0.1:8000/ws/broadcast/smoke-room?client_id=publisher&deterministic=true") as publisher:
            publisher_welcome = json.loads(await asyncio.wait_for(publisher.recv(), timeout=3))
            assert publisher_welcome["event"] == "welcome"
            await publisher.send("smoke-broadcast")
            subscriber_message = json.loads(await asyncio.wait_for(subscriber.recv(), timeout=3))
            assert subscriber_message["event"] == "broadcast"
            assert subscriber_message["message"] == "smoke-broadcast"

asyncio.run(main())
PY
    return 0
  fi
  if [[ "${method}" == "POST" ]]; then
    curl -fsS --max-time "${CURL_MAX_TIME_SECONDS}" \
      -H "Content-Type: application/json" \
      -X POST \
      -d "${payload}" \
      "${url}" >/dev/null
    return 0
  fi

  curl -fsS --max-time "${CURL_MAX_TIME_SECONDS}" "${url}" >/dev/null
}

echo "== docker compose config =="
docker compose -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" config --quiet

echo "== docker compose build =="
run_with_timeout "${BUILD_TIMEOUT_SECONDS}" docker compose -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" build

echo "== docker compose up =="
run_with_timeout "${UP_TIMEOUT_SECONDS}" docker compose -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" up -d

for service_entry in "${SERVICES[@]}"; do
  IFS="|" read -r name health_url representative_method representative_url representative_payload <<<"${service_entry}"
  retry_health "${name}" "${health_url}"
  echo "representative ok: ${name}"
  call_representative "${representative_method}" "${representative_url}" "${representative_payload}"
done

echo "docker target-apps smoke validation passed"
