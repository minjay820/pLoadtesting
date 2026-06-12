# JMeter Observability Validation

Use this runbook when a JMeter task appears to finish in the Control Plane but Grafana does not show the expected results.

## What Changed

- The JMeter plan now resolves `TARGET_HOST` and `TARGET_PORT` from JVM properties first, with `localhost:8000` as fallback.
- The worker still launches JMeter with `-JTARGET_HOST` and `-JTARGET_PORT`, so Control Plane task targets can now override the plan correctly.
- Grafana summary panels now read `task_summary` from the `load_tests` bucket, which is written for both k6 and JMeter after task completion.
- Grafana should run on `11.6.11` or newer to avoid the `react/jsx-runtime` frontend regression seen on `11.6.0`. In Docker Compose, use the published image tag `grafana/grafana:11.6.11`.
- The provisioned InfluxDB datasource should use the fixed UID `influxdb-ploadtesting`, and the dashboard should reference that UID directly instead of a datasource template variable.

## Validation Flow

1. Confirm the stack is healthy.
   ```bash
   docker compose ps
   ```
2. Create a JMeter task against the container-reachable target.
   ```bash
   curl -s -X POST http://127.0.0.1:9000/api/tasks/ \
     -H 'Content-Type: application/json' \
     -H 'X-PLOADTESTING-API-TOKEN: dev-api-token-change-me' \
     -d '{
       "name": "JMeter validation",
       "engine": "jmeter",
       "script_path": "engines/jmeter/ploadtesting_test_plan.jmx",
       "target_url": "http://target-app:8000",
       "parameters": { "target_url": "http://target-app:8000" },
       "created_by": "codex"
     }'
   ```
3. Watch the worker log for the effective JMeter command and result post.
   ```bash
   docker logs ploadtesting-worker-agent-1 --tail=200
   ```
4. Confirm the task result shows non-zero top-level counters.
   ```bash
   curl -s http://127.0.0.1:9000/api/tasks/<task-id>/ \
     -H 'X-PLOADTESTING-API-TOKEN: dev-api-token-change-me'
   ```
5. Confirm InfluxDB has a `task_summary` point for the task.
   ```bash
   docker exec ploadtesting-influxdb influx query \
     'from(bucket:"load_tests")
       |> range(start: -30m)
       |> filter(fn: (r) => r._measurement == "task_summary")
       |> filter(fn: (r) => r.task_id == "<task-id>")' \
     --org ploadtesting \
     --token ploadtesting-dev-token
   ```
6. Reload Grafana and verify the top summary panels update.

## Browser-Side Caveat

- The Grafana datasource query path can be healthy even when the Codex in-app browser still shows `No data`.
- In this repository, two separate browser-side failure modes were observed:
  - Grafana `11.6.0` could trip a frontend `/react/jsx-runtime` `404`.
  - Dashboard panels that referenced the datasource through `${DS_INFLUXDB-PLOADTESTING}` could fail before issuing `/api/ds/query` requests, even after Grafana was upgraded.
- Keep the dashboard pinned to the fixed datasource UID `influxdb-ploadtesting` and verify the panel query directly before assuming InfluxDB or JMeter is broken:
  ```bash
  curl -s -u admin:admin http://127.0.0.1:3000/api/ds/query \
    -H 'Content-Type: application/json' \
    -d '{
      "queries": [{
        "refId": "A",
        "datasource": { "uid": "influxdb-ploadtesting", "type": "influxdb" },
        "datasourceId": 1,
        "query": "from(bucket: \"load_tests\") |> range(start: -30m) |> filter(fn: (r) => r[\"_measurement\"] == \"task_summary\")",
        "intervalMs": 60000,
        "maxDataPoints": 500
      }],
      "from": "now-30m",
      "to": "now"
    }'
  ```
- If the API returns frames but the in-app browser still renders `No data`, inspect browser console errors and confirm the dashboard is not still using datasource template indirection.

## Expected Signals

- Worker command includes `-JTARGET_HOST=target-app -JTARGET_PORT=8000`.
- JTL rows reference `http://target-app:8000/...`, not `http://localhost:8000/...`.
- Control Plane result contains top-level `total_requests`, `failed_requests`, and `error_rate_pct`.
- Grafana overview panels show the latest completed task metrics instead of `No data`.
