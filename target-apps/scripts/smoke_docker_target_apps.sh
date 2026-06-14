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
  "payload-api|http://127.0.0.1:18084/health|GET|http://127.0.0.1:18084/api/download?kb=4|"
  "crud-api|http://127.0.0.1:18085/health|GET|http://127.0.0.1:18085/api/items|"
  "auth-flow-api|http://127.0.0.1:18086/health|POST|http://127.0.0.1:18086/api/login|{\"username\":\"smoke\",\"password\":\"demo-password\"}"
  "sse-api|http://127.0.0.1:18087/health|GET|http://127.0.0.1:18087/api/events?count=2&interval_ms=1|"
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
