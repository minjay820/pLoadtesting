from unittest import mock
from datetime import timedelta
from urllib.error import URLError

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.results.models import TestResult
from apps.tasks.execution import ENGINE_DEFAULT_EXECUTION
from apps.tasks.models import LoadTestTask
from apps.tasks.tasks import dispatch_pending_tasks
from apps.workers.models import WorkerNode


API_TOKEN = "test-token"


@override_settings(PLOADTESTING_API_TOKEN=API_TOKEN)
class ApiSecurityTests(TestCase):
    def test_api_requires_shared_token(self):
        response = APIClient().get("/api/workers/")

        self.assertEqual(response.status_code, 403)


class DispatchPendingTasksTests(TestCase):
    def create_task(self, engine="k6"):
        return LoadTestTask.objects.create(
            name=f"{engine} smoke",
            engine=engine,
            script_path=f"{engine}/smoke.js",
            target_url="http://target-app:8000",
        )

    def create_worker(self, *, name, capabilities, active_task_count=0):
        return WorkerNode.objects.create(
            name=name,
            ip_address="127.0.0.1",
            port=8100,
            status=WorkerNode.Status.ONLINE,
            capabilities=capabilities,
            active_task_count=active_task_count,
        )

    @mock.patch("apps.tasks.tasks.urllib.request.urlopen", side_effect=URLError("connection refused"))
    def test_dispatch_failure_leaves_task_pending_for_retry(self, mocked_urlopen):
        self.create_worker(name="k6-worker", capabilities=["k6"])
        task = self.create_task("k6")

        dispatched_count = dispatch_pending_tasks()

        task.refresh_from_db()
        self.assertEqual(dispatched_count, 0)
        self.assertEqual(task.status, LoadTestTask.Status.PENDING)
        self.assertIsNone(task.worker)
        self.assertIn("Dispatch to worker", task.error_message)
        mocked_urlopen.assert_called_once()

    @mock.patch("apps.tasks.tasks.urllib.request.urlopen")
    def test_dispatch_uses_idle_compatible_worker_only(self, mocked_urlopen):
        incompatible = self.create_worker(name="jmeter-worker", capabilities=["jmeter"])
        busy_compatible = self.create_worker(
            name="busy-k6-worker",
            capabilities=["k6"],
            active_task_count=1,
        )
        idle_compatible = self.create_worker(name="idle-k6-worker", capabilities=["k6"])
        task = self.create_task("k6")
        mocked_urlopen.return_value.__enter__.return_value.status = 202

        dispatched_count = dispatch_pending_tasks()

        task.refresh_from_db()
        self.assertEqual(dispatched_count, 1)
        self.assertEqual(task.status, LoadTestTask.Status.DISPATCHED)
        self.assertEqual(task.worker, idle_compatible)
        self.assertNotEqual(task.worker, incompatible)
        self.assertNotEqual(task.worker, busy_compatible)
        self.assertEqual(task.error_message, "")


@override_settings(PLOADTESTING_API_TOKEN=API_TOKEN)
class TaskResultCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_X_PLOADTESTING_API_TOKEN=API_TOKEN)

    def test_failed_worker_result_marks_task_failed(self):
        task = LoadTestTask.objects.create(
            name="failing k6 run",
            engine="k6",
            script_path="k6/missing.js",
            target_url="http://target-app:8000",
            status=LoadTestTask.Status.DISPATCHED,
        )

        response = self.client.post(
            f"/api/tasks/{task.id}/results/",
            {
                "execution_status": "failed",
                "error_message": "k6 exited with code 107",
                "raw_report": {"stderr": "script not found", "exit_code": 107},
            },
            format="json",
        )

        task.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(TestResult.objects.filter(task=task).exists())
        self.assertEqual(task.status, LoadTestTask.Status.FAILED)
        self.assertEqual(task.error_message, "k6 exited with code 107")


@override_settings(PLOADTESTING_API_TOKEN=API_TOKEN)
class TaskReadContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_X_PLOADTESTING_API_TOKEN=API_TOKEN)

    def create_task(self, *, name="history task", status=LoadTestTask.Status.PENDING):
        return LoadTestTask.objects.create(
            name=name,
            engine="k6",
            script_path="engines/k6/target_apps_payload_download.js",
            target_url="http://127.0.0.1:18084",
            status=status,
            parameters={
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-download",
                "TARGET_URL": "http://127.0.0.1:18084",
                "execution": {
                    "duration_seconds": 600,
                    "ramp_up_seconds": 30,
                    "ramp_down_seconds": 0,
                    "stop_policy": "graceful_stop",
                    "graceful_stop_seconds": 30,
                    "max_run_seconds": 660,
                    "iteration_limit": None,
                    "data_policy": "duration_first",
                },
                "distribution": {
                    "mode": "manual_shards",
                    "result_merge_policy": "summary_only",
                    "shards": [
                        {
                            "shard_id": "users-a",
                            "agent_selector": {"labels": ["zone:a", "engine:k6"]},
                            "dataset": {
                                "source": "artifact://datasets/users.csv",
                                "format": "csv",
                                "offset": 0,
                                "limit": 2000,
                            },
                        }
                    ],
                },
            },
        )

    def create_jmeter_task(self, *, name="jmeter history task", status=LoadTestTask.Status.PENDING):
        return LoadTestTask.objects.create(
            name=name,
            engine="jmeter",
            script_path="engines/jmeter/target_apps_payload_crud_plan.jmx",
            target_url="http://127.0.0.1:18084",
            status=status,
            parameters={
                "target_app_id": "payload-api",
                "target_profile_id": "payload-jmeter-download",
                "target_url": "http://127.0.0.1:18084",
            },
        )

    def test_task_history_returns_read_model_envelope(self):
        self.create_task(name="first task")

        response = self.client.get("/api/tasks/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"]["status"], "ok")
        self.assertEqual(payload["summary"]["count"], 1)
        self.assertEqual(payload["summary"]["limit"], 20)
        self.assertEqual(payload["summary"]["total_available"], 1)
        self.assertEqual(payload["items"][0]["target_app_id"], "payload-api")
        self.assertEqual(payload["items"][0]["target_profile_id"], "payload-k6-download")
        self.assertEqual(payload["items"][0]["engine"], "k6")

    def test_task_history_limit_bounds_items(self):
        for index in range(3):
            self.create_task(name=f"task {index}")

        response = self.client.get("/api/tasks/?limit=2")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["count"], 2)
        self.assertEqual(payload["summary"]["limit"], 2)
        self.assertEqual(payload["summary"]["total_available"], 3)
        self.assertEqual(len(payload["items"]), 2)

    def test_task_history_status_filter(self):
        self.create_task(name="queued task", status=LoadTestTask.Status.PENDING)
        self.create_task(name="failed task", status=LoadTestTask.Status.FAILED)

        response = self.client.get("/api/tasks/?status=failed")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["count"], 1)
        self.assertEqual(payload["items"][0]["status"], "failed")

    def test_task_detail_returns_normalized_read_model(self):
        task = self.create_task()

        response = self.client.get(f"/api/tasks/{task.id}/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"]["status"], "ok")
        self.assertEqual(payload["task"]["id"], str(task.id))
        self.assertEqual(payload["task"]["target_app_id"], "payload-api")
        self.assertEqual(payload["task"]["target_profile_id"], "payload-k6-download")
        self.assertEqual(payload["execution"]["duration_seconds"], 600)
        self.assertEqual(payload["distribution"]["mode"], "manual_shards")
        self.assertEqual(payload["parameters"]["has_execution"], True)
        self.assertEqual(payload["parameters"]["has_distribution"], True)
        self.assertEqual(payload["result"]["status"], "not_available")

    def test_missing_task_read_endpoints_return_404(self):
        missing = "00000000-0000-0000-0000-000000000000"

        for path in (
            f"/api/tasks/{missing}/",
            f"/api/tasks/{missing}/result-summary/",
            f"/api/tasks/{missing}/artifacts/",
            f"/api/tasks/{missing}/artifacts/any/download/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)

    def test_result_summary_returns_not_available_placeholder(self):
        task = self.create_task()

        response = self.client.get(f"/api/tasks/{task.id}/result-summary/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"]["status"], "ok")
        self.assertEqual(payload["task_id"], str(task.id))
        self.assertEqual(payload["status"], "not_available")
        self.assertIsNone(payload["summary"]["total_requests"])
        self.assertIsNone(payload["latency"]["p95_ms"])
        self.assertEqual(payload["provenance"]["engine"], "k6")
        self.assertIsNone(payload["provenance"]["metrics_source"])
        self.assertEqual(payload["warnings"][0]["code"], "result_summary_not_available")

    def test_result_summary_maps_existing_result(self):
        task = self.create_task(status=LoadTestTask.Status.COMPLETED)
        task.started_at = timezone.now()
        task.finished_at = task.started_at + timedelta(seconds=60)
        task.save(update_fields=["started_at", "finished_at", "updated_at"])
        result = TestResult.objects.create(
            task=task,
            raw_report={"message": "complete"},
            total_requests=100,
            failed_requests=3,
            error_rate_pct=3.0,
            avg_response_ms=120.5,
            p90_response_ms=200.0,
            p95_response_ms=240.0,
            p99_response_ms=300.0,
            max_response_ms=450.0,
            throughput_rps=1.67,
            thresholds_passed=True,
            thresholds_detail=[{"metric": "p95", "passed": True}],
        )

        response = self.client.get(f"/api/tasks/{task.id}/result-summary/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["summary"]["total_requests"], 100)
        self.assertEqual(payload["summary"]["total_errors"], 3)
        self.assertEqual(payload["summary"]["duration_seconds"], 60.0)
        self.assertEqual(payload["latency"]["avg_ms"], 120.5)
        self.assertEqual(payload["latency"]["p95_ms"], 240.0)
        self.assertIsNone(payload["latency"]["p50_ms"])
        self.assertEqual(payload["provenance"]["metrics_source"], "test_result")
        self.assertEqual(payload["provenance"]["engine"], "k6")
        self.assertEqual(payload["provenance"]["percentile_policy"], "engine_reported")
        self.assertEqual(payload["thresholds"]["passed"], True)
        self.assertEqual(payload["summary"]["collected_at"], result.collected_at.isoformat().replace("+00:00", "Z"))
        self.assertEqual(payload["warnings"][0]["code"], "percentiles_engine_reported")
        self.assertEqual(payload["warnings"][1]["code"], "p50_not_available")

    def test_artifacts_returns_planned_rows_without_result(self):
        task = self.create_task()

        response = self.client.get(f"/api/tasks/{task.id}/artifacts/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"]["status"], "ok")
        self.assertEqual(payload["task_id"], str(task.id))
        self.assertEqual(payload["summary"]["count"], 5)
        self.assertEqual(payload["summary"]["available_count"], 0)
        self.assertEqual(payload["summary"]["missing_count"], 0)
        self.assertEqual(payload["warnings"], [])
        items = {item["artifact_id"]: item for item in payload["items"]}
        self.assertEqual(set(items), {"k6-summary-json", "k6-stdout", "k6-stderr", "k6-engine-output", "k6-html-report"})
        self.assertEqual(items["k6-summary-json"]["kind"], "summary_json")
        self.assertEqual(items["k6-summary-json"]["state"], "planned")
        self.assertEqual(items["k6-summary-json"]["download_available"], False)
        self.assertIsNone(items["k6-summary-json"]["download_url"])
        self.assertEqual(items["k6-summary-json"]["provenance"]["source"], "engine_convention")
        self.assertEqual(items["k6-engine-output"]["kind"], "engine_output")
        self.assertEqual(items["k6-html-report"]["kind"], "html_report")

    def test_artifacts_derive_available_rows_from_raw_report_only(self):
        task = self.create_task(status=LoadTestTask.Status.COMPLETED)
        TestResult.objects.create(
            task=task,
            raw_report={"stdout": "ok", "stderr": "warn", "message": "complete"},
            total_requests=10,
            failed_requests=0,
        )

        response = self.client.get(f"/api/tasks/{task.id}/artifacts/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["count"], 5)
        self.assertEqual(payload["summary"]["available_count"], 3)
        self.assertEqual(payload["summary"]["missing_count"], 1)
        items = {item["artifact_id"]: item for item in payload["items"]}
        self.assertEqual(items["k6-stdout"]["state"], "available")
        self.assertEqual(items["k6-stderr"]["state"], "available")
        self.assertEqual(items["k6-engine-output"]["state"], "available")
        self.assertEqual(items["k6-summary-json"]["state"], "missing")
        self.assertEqual(items["k6-html-report"]["state"], "planned")
        self.assertEqual(items["k6-engine-output"]["provenance"]["source"], "result_raw_report")
        self.assertIsNotNone(items["k6-stdout"]["created_at"])

    def test_artifacts_include_jmeter_kinds(self):
        task = self.create_jmeter_task()

        response = self.client.get(f"/api/tasks/{task.id}/artifacts/")

        self.assertEqual(response.status_code, 200)
        items = {item["artifact_id"]: item for item in response.json()["items"]}
        self.assertEqual(set(items), {"jmeter-jtl", "jmeter-raw-log", "jmeter-stdout", "jmeter-stderr", "jmeter-engine-output", "jmeter-html-report"})
        self.assertEqual(items["jmeter-jtl"]["kind"], "jtl")
        self.assertEqual(items["jmeter-raw-log"]["kind"], "raw_log")
        self.assertEqual(items["jmeter-html-report"]["state"], "planned")

    def test_artifacts_unknown_engine_falls_back_safely(self):
        task = LoadTestTask.objects.create(
            name="unknown engine task",
            engine="loadrunner",
            script_path="engines/loadrunner/demo",
            target_url="http://127.0.0.1:18084",
        )

        response = self.client.get(f"/api/tasks/{task.id}/artifacts/")

        self.assertEqual(response.status_code, 200)
        items = {item["artifact_id"]: item for item in response.json()["items"]}
        self.assertEqual(items["engine-output"]["kind"], "engine_output")
        self.assertEqual(items["unknown-artifact"]["kind"], "unknown")
        self.assertEqual(items["unknown-artifact"]["state"], "planned")

    def test_artifact_download_placeholder_returns_501(self):
        task = self.create_task()

        response = self.client.get(f"/api/tasks/{task.id}/artifacts/k6-summary-json/download/")

        self.assertEqual(response.status_code, 501)
        payload = response.json()
        self.assertEqual(payload["source"]["status"], "ok")
        self.assertEqual(payload["task_id"], str(task.id))
        self.assertEqual(payload["artifact_id"], "k6-summary-json")
        self.assertEqual(payload["status"], "not_implemented")
        self.assertEqual(payload["download_available"], False)
        self.assertEqual(payload["warnings"][0]["code"], "artifact_download_not_implemented")
        self.assertNotIn("/tmp/", str(payload))


@override_settings(PLOADTESTING_API_TOKEN=API_TOKEN)
class TaskTemplateApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_X_PLOADTESTING_API_TOKEN=API_TOKEN)

    def manual_distribution(self):
        return {
            "mode": "manual_shards",
            "result_merge_policy": "summary_only",
            "shards": [
                {
                    "shard_id": "users-a",
                    "agent_selector": {"labels": ["zone:a", "engine:k6"]},
                    "dataset": {
                        "source": "artifact://datasets/users.csv",
                        "format": "csv",
                        "offset": 0,
                        "limit": 2000,
                    },
                },
                {
                    "shard_id": "users-b",
                    "agent_selector": {"labels": ["zone:b", "engine:k6"]},
                    "dataset": {
                        "source": "artifact://datasets/users.csv",
                        "format": "csv",
                        "offset": 2000,
                        "limit": 3000,
                    },
                },
            ],
        }

    def test_list_task_templates(self):
        response = self.client.get("/api/tasks/templates/")

        self.assertEqual(response.status_code, 200)
        templates = response.json()["templates"]
        self.assertTrue(any(row["target_profile_id"] == "echo-k6-smoke" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "payload-jmeter-download" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "payload-k6-download" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "payload-k6-file-download" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "payload-k6-archive-read-many" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "auth-k6-refresh-flow" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "auth-k6-failure-branches" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "auth-k6-session-flow" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "auth-k6-mfa-flow" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "error-jmeter-flaky" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "resource-jmeter-cpu" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "payload-jmeter-archive-read-many" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "payload-jmeter-file-roundtrip" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "payload-k6-tar-selective-fetch" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "payload-jmeter-tar-selective-fetch" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "crud-jmeter-flow" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "auth-jmeter-checkout" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "auth-jmeter-failure-branches" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "auth-jmeter-refresh-flow" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "auth-jmeter-session-flow" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "auth-jmeter-mfa-flow" for row in templates))
        self.assertTrue(any(row["target_app_id"] == "sse-api" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "sse-jmeter-ticker" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "sse-k6-progress-heavy" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "sse-jmeter-progress-heavy" for row in templates))
        self.assertTrue(any(row["target_app_id"] == "ws-api" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "ws-jmeter-echo-smoke" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "ws-jmeter-broadcast-smoke" for row in templates))
        self.assertTrue(any(row["target_app_id"] == "db-api" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "db-jmeter-crud-smoke" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "db-jmeter-list-filter" for row in templates))
        templates_by_profile = {row["target_profile_id"]: row for row in templates}
        self.assertEqual(templates_by_profile["sse-k6-ticker"]["equivalent_profile_id"], "sse-jmeter-ticker")
        self.assertEqual(
            templates_by_profile["auth-k6-failure-branches"]["equivalent_profile_id"],
            "auth-jmeter-failure-branches",
        )
        self.assertEqual(templates_by_profile["crud-k6-flow"]["equivalent_profile_id"], "crud-jmeter-flow")
        self.assertEqual(templates_by_profile["ws-k6-echo-smoke"]["equivalent_profile_id"], "ws-jmeter-echo-smoke")
        self.assertEqual(
            templates_by_profile["payload-k6-archive-read-many"]["equivalent_profile_id"],
            "payload-jmeter-archive-read-many",
        )
        self.assertEqual(
            templates_by_profile["payload-jmeter-download"]["equivalent_profile_id"],
            "payload-k6-download",
        )
        self.assertEqual(
            templates_by_profile["payload-k6-download"]["equivalent_profile_id"],
            "payload-jmeter-download",
        )
        self.assertEqual(templates_by_profile["payload-k6-download"]["coverage_status"], "exact")
        self.assertEqual(templates_by_profile["payload-jmeter-download"]["coverage_status"], "exact")
        self.assertEqual(templates_by_profile["payload-k6-download"]["coverage_group"], "payload.download")
        self.assertIsNone(templates_by_profile["payload-k6-download"]["coverage_gap"])

    def test_template_coverage_export(self):
        response = self.client.get("/api/tasks/templates/coverage/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            payload["summary"],
            {
                "target_app_count": 10,
                "profile_count": 44,
                "k6_profile_count": 22,
                "jmeter_profile_count": 22,
                "exact_coverage_profile_count": 44,
                "gap_profile_count": 0,
            },
        )
        self.assertEqual(payload["gaps"], [])
        self.assertEqual(len(payload["profiles"]), 44)
        self.assertEqual(len(payload["targets"]), 10)

        required_summary_fields = {
            "target_app_count",
            "profile_count",
            "k6_profile_count",
            "jmeter_profile_count",
            "exact_coverage_profile_count",
            "gap_profile_count",
        }
        self.assertEqual(set(payload["summary"]), required_summary_fields)

        required_profile_fields = {
            "target_app_id",
            "target_profile_id",
            "engine",
            "script_path",
            "coverage_status",
            "coverage_group",
            "coverage_gap",
        }
        profile_keys = {(row["target_app_id"], row["target_profile_id"]) for row in payload["profiles"]}
        for profile in payload["profiles"]:
            self.assertTrue(required_profile_fields.issubset(profile))
            self.assertIn(profile["coverage_status"], {"exact", "gap"})
            self.assertTrue(profile["coverage_group"])
            if profile["coverage_status"] == "exact":
                equivalent_profile_id = profile.get("equivalent_profile_id")
                self.assertTrue(equivalent_profile_id)
                equivalent_key = (profile["target_app_id"], equivalent_profile_id)
                self.assertIn(equivalent_key, profile_keys)

        profiles_by_id = {row["target_profile_id"]: row for row in payload["profiles"]}
        self.assertEqual(profiles_by_id["payload-k6-download"]["coverage_status"], "exact")
        self.assertEqual(profiles_by_id["payload-k6-download"]["coverage_group"], "payload.download")
        self.assertEqual(profiles_by_id["payload-k6-download"]["equivalent_profile_id"], "payload-jmeter-download")
        self.assertIsNone(profiles_by_id["payload-k6-download"]["coverage_gap"])

        targets_by_id = {row["target_app_id"]: row for row in payload["targets"]}
        self.assertEqual(targets_by_id["payload-api"]["profile_count"], 10)
        self.assertEqual(targets_by_id["payload-api"]["k6_profile_count"], 5)
        self.assertEqual(targets_by_id["payload-api"]["jmeter_profile_count"], 5)
        self.assertEqual(targets_by_id["payload-api"]["gap_profile_count"], 0)
        self.assertEqual(targets_by_id["payload-api"]["exact_coverage_profile_count"], 10)

    def test_create_task_accepts_valid_execution_object(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-download",
                "execution": {
                    "duration_seconds": 600,
                    "ramp_up_seconds": 30,
                    "ramp_down_seconds": 15,
                    "stop_policy": "graceful_stop",
                    "graceful_stop_seconds": 30,
                    "max_run_seconds": 690,
                    "iteration_limit": None,
                    "data_policy": "duration_first",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(
            task.parameters["execution"],
            {
                "duration_seconds": 600,
                "ramp_up_seconds": 30,
                "ramp_down_seconds": 15,
                "stop_policy": "graceful_stop",
                "graceful_stop_seconds": 30,
                "max_run_seconds": 690,
                "iteration_limit": None,
                "data_policy": "duration_first",
            },
        )

    def test_request_execution_overrides_template_default(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "echo-api",
                "target_profile_id": "echo-k6-smoke",
                "execution": {
                    "duration_seconds": 45,
                    "ramp_up_seconds": 5,
                    "ramp_down_seconds": 0,
                    "stop_policy": "hard_stop",
                    "graceful_stop_seconds": 0,
                    "max_run_seconds": 45,
                    "iteration_limit": None,
                    "data_policy": "duration_first",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.parameters["execution"]["duration_seconds"], 45)
        self.assertEqual(task.parameters["execution"]["stop_policy"], "hard_stop")
        self.assertEqual(task.parameters["execution"]["max_run_seconds"], 45)

    def test_missing_execution_uses_engine_default(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "name": "manual k6 task",
                "engine": "k6",
                "script_path": "engines/k6/target_apps_db_list_filter.js",
                "target_url": "http://127.0.0.1:18089",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.parameters["execution"], ENGINE_DEFAULT_EXECUTION["k6"])

    def test_invalid_stop_policy_is_rejected(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-download",
                "execution": {
                    "duration_seconds": 10,
                    "ramp_up_seconds": 0,
                    "ramp_down_seconds": 0,
                    "stop_policy": "drain_inflight",
                    "graceful_stop_seconds": 10,
                    "max_run_seconds": 30,
                    "iteration_limit": None,
                    "data_policy": "duration_first",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("future policy", str(response.json()))

    def test_invalid_duration_is_rejected(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-download",
                "execution": {
                    "duration_seconds": 0,
                    "ramp_up_seconds": 0,
                    "ramp_down_seconds": 0,
                    "stop_policy": "graceful_stop",
                    "graceful_stop_seconds": 10,
                    "max_run_seconds": 30,
                    "iteration_limit": None,
                    "data_policy": "duration_first",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("duration_seconds", str(response.json()))

    def test_max_run_seconds_must_cover_duration_and_grace(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-download",
                "execution": {
                    "duration_seconds": 20,
                    "ramp_up_seconds": 0,
                    "ramp_down_seconds": 0,
                    "stop_policy": "graceful_stop",
                    "graceful_stop_seconds": 10,
                    "max_run_seconds": 29,
                    "iteration_limit": None,
                    "data_policy": "duration_first",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("max_run_seconds", str(response.json()))

    def test_template_list_includes_profile_default_execution(self):
        response = self.client.get("/api/tasks/templates/")

        self.assertEqual(response.status_code, 200)
        templates_by_profile = {row["target_profile_id"]: row for row in response.json()["templates"]}
        execution = templates_by_profile["payload-k6-download"]["execution"]
        self.assertEqual(execution["duration_seconds"], 10)
        self.assertEqual(execution["stop_policy"], "graceful_stop")

    def test_create_task_accepts_distribution_and_builds_shard_plan(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "auth-flow-api",
                "target_profile_id": "auth-k6-refresh-flow",
                "distribution": self.manual_distribution(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        distribution = task.parameters["distribution"]
        self.assertEqual(distribution["mode"], "manual_shards")
        self.assertEqual(distribution["result_merge_policy"], "summary_only")
        self.assertEqual(len(distribution["shards"]), 2)

        plan = task.parameters["shard_execution_plan"]
        self.assertEqual(plan["distribution"]["shard_count"], 2)
        self.assertEqual(plan["result_aggregation"]["policy"], "summary_only")
        self.assertEqual(plan["result_aggregation"]["shard_count"], 2)
        self.assertEqual(plan["shards"][0]["shard_id"], "users-a")
        self.assertEqual(plan["shards"][0]["target_app_id"], "auth-flow-api")
        self.assertEqual(plan["shards"][0]["target_profile_id"], "auth-k6-refresh-flow")
        self.assertEqual(plan["shards"][0]["dataset"]["offset"], 0)
        self.assertEqual(plan["shards"][1]["dataset"]["limit"], 3000)

        plan_response = self.client.get(f"/api/tasks/{task.id}/shard-plan/")
        self.assertEqual(plan_response.status_code, 200)
        self.assertEqual(plan_response.json(), plan)

    def test_create_task_combines_execution_and_distribution(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-download",
                "execution": {
                    "duration_seconds": 600,
                    "ramp_up_seconds": 30,
                    "ramp_down_seconds": 0,
                    "stop_policy": "graceful_stop",
                    "graceful_stop_seconds": 30,
                    "max_run_seconds": 660,
                    "iteration_limit": None,
                    "data_policy": "duration_first",
                },
                "distribution": self.manual_distribution(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        shard = task.parameters["shard_execution_plan"]["shards"][0]
        self.assertEqual(shard["execution"]["duration_seconds"], 600)
        self.assertEqual(shard["execution"]["max_run_seconds"], 660)

    def test_duplicate_shard_id_is_rejected(self):
        distribution = self.manual_distribution()
        distribution["shards"][1]["shard_id"] = "users-a"

        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-download",
                "distribution": distribution,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Duplicate shard_id", str(response.json()))

    def test_distribution_dataset_validation_rejects_invalid_values(self):
        cases = [
            ("offset", -1, "offset"),
            ("limit", 0, "limit"),
            ("format", "parquet", "format"),
            ("source", "/tmp/users.csv", "source"),
        ]

        for field, value, expected_message in cases:
            with self.subTest(field=field):
                distribution = self.manual_distribution()
                distribution["shards"][0]["dataset"][field] = value
                response = self.client.post(
                    "/api/tasks/",
                    {
                        "target_app_id": "payload-api",
                        "target_profile_id": "payload-k6-download",
                        "distribution": distribution,
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn(expected_message, str(response.json()))

    def test_distribution_agent_selector_labels_must_be_string_array(self):
        distribution = self.manual_distribution()
        distribution["shards"][0]["agent_selector"]["labels"] = "zone:a"

        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-download",
                "distribution": distribution,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("string array", str(response.json()))

    def test_create_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "echo-api",
                "target_profile_id": "echo-k6-smoke",
                "created_by": "template-test",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.name, "Echo Smoke via k6")
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_echo_smoke.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18080")
        self.assertEqual(task.parameters["TARGET_URL"], "http://127.0.0.1:18080")
        self.assertEqual(task.parameters["target_url"], "http://127.0.0.1:18080")
        self.assertNotIn("shard_execution_plan", task.parameters)

        plan_response = self.client.get(f"/api/tasks/{task.id}/shard-plan/")
        self.assertEqual(plan_response.status_code, 404)


    def test_create_crud_jmeter_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "crud-api",
                "target_profile_id": "crud-jmeter-flow",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "jmeter")
        self.assertEqual(task.script_path, "engines/jmeter/target_apps_crud_flow_plan.jmx")
        self.assertEqual(task.parameters["ITEM_NAME"], "smoke-item")

    def test_create_payload_file_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-file-roundtrip",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_payload_file_flow.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18084")
        self.assertEqual(task.parameters["FILE_UPLOAD_MODE"], "1")

    def test_create_payload_download_tasks_from_templates(self):
        k6_response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-download",
            },
            format="json",
        )
        jmeter_response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-jmeter-download",
            },
            format="json",
        )

        self.assertEqual(k6_response.status_code, 201)
        self.assertEqual(jmeter_response.status_code, 201)
        k6_task = LoadTestTask.objects.get(id=k6_response.json()["id"])
        jmeter_task = LoadTestTask.objects.get(id=jmeter_response.json()["id"])
        self.assertEqual(k6_task.engine, "k6")
        self.assertEqual(k6_task.script_path, "engines/k6/target_apps_payload_download.js")
        self.assertEqual(k6_task.parameters["PAYLOAD_KB"], "32")
        self.assertEqual(jmeter_task.engine, "jmeter")
        self.assertEqual(jmeter_task.script_path, "engines/jmeter/target_apps_payload_crud_plan.jmx")
        self.assertEqual(jmeter_task.parameters["TARGET_PATH"], "/api/download")

    def test_create_payload_archive_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-k6-archive-read-many",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_payload_archive_flow.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18084")
        self.assertEqual(task.parameters["PACK_COUNT"], "4")

    def test_create_payload_tar_selective_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "payload-api",
                "target_profile_id": "payload-jmeter-tar-selective-fetch",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "jmeter")
        self.assertEqual(task.script_path, "engines/jmeter/target_apps_payload_flow_plan.jmx")
        self.assertEqual(task.parameters["FLOW_MODE"], "tar-selective")
        self.assertEqual(task.parameters["SELECTIVE_COUNT"], "3")

    def test_create_task_from_template_with_overrides(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "latency-api",
                "target_profile_id": "latency-k6-delay",
                "name": "Custom Latency Task",
                "target_url": "http://127.0.0.1:19081",
                "parameters": {
                    "TARGET_URL": "http://127.0.0.1:19081",
                    "DELAY_MS": "400",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.name, "Custom Latency Task")
        self.assertEqual(task.target_url, "http://127.0.0.1:19081")
        self.assertEqual(task.parameters["TARGET_URL"], "http://127.0.0.1:19081")
        self.assertEqual(task.parameters["DELAY_MS"], "400")
        self.assertEqual(task.parameters["target_url"], "http://127.0.0.1:19081")

    def test_template_fields_must_be_complete(self):
        response = self.client.post(
            "/api/tasks/",
            {"target_app_id": "echo-api"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("target_app_id and target_profile_id", str(response.json()))

    def test_create_sse_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "sse-api",
                "target_profile_id": "sse-k6-smoke",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.name, "SSE Smoke via k6")
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_sse_smoke.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18087")
        self.assertEqual(task.parameters["SSE_ENDPOINT_PATH"], "/api/events")

    def test_create_progress_heavy_sse_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "sse-api",
                "target_profile_id": "sse-k6-progress-heavy",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.script_path, "engines/k6/target_apps_sse_smoke.js")
        self.assertEqual(task.parameters["SSE_ENDPOINT_PATH"], "/api/progress-heavy")
        self.assertEqual(task.parameters["SSE_STEPS"], "24")

    def test_create_progress_heavy_sse_jmeter_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "sse-api",
                "target_profile_id": "sse-jmeter-progress-heavy",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "jmeter")
        self.assertEqual(task.script_path, "engines/jmeter/target_apps_sse_plan.jmx")
        self.assertEqual(task.parameters["SSE_ENDPOINT_PATH"], "/api/progress-heavy")
        self.assertEqual(task.parameters["SSE_STEPS"], "24")

    def test_create_ticker_sse_jmeter_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "sse-api",
                "target_profile_id": "sse-jmeter-ticker",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "jmeter")
        self.assertEqual(task.script_path, "engines/jmeter/target_apps_sse_plan.jmx")
        self.assertEqual(task.parameters["SSE_ENDPOINT_PATH"], "/api/ticker")
        self.assertEqual(task.parameters["SSE_COUNT"], "6")

    def test_create_ws_echo_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "ws-api",
                "target_profile_id": "ws-k6-echo-smoke",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_ws_echo_smoke.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18088")
        self.assertEqual(task.parameters["WS_PATH"], "/ws/echo")

    def test_create_ws_broadcast_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "ws-api",
                "target_profile_id": "ws-k6-broadcast-smoke",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_ws_broadcast_smoke.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18088")
        self.assertEqual(task.parameters["WS_ROOM"], "smoke-room")

    def test_create_ws_jmeter_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "ws-api",
                "target_profile_id": "ws-jmeter-broadcast-smoke",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "jmeter")
        self.assertEqual(task.script_path, "engines/jmeter/target_apps_ws_flow_plan.jmx")
        self.assertEqual(task.target_url, "http://127.0.0.1:18088")
        self.assertEqual(task.parameters["FLOW_MODE"], "broadcast")
        self.assertEqual(task.parameters["WS_ROOM"], "smoke-room")

    def test_create_db_crud_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "db-api",
                "target_profile_id": "db-k6-crud-smoke",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_db_crud_flow.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18089")
        self.assertEqual(task.parameters["DB_RECORD_NAME"], "smoke-record")

    def test_create_db_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "db-api",
                "target_profile_id": "db-k6-list-filter",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_db_list_filter.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18089")
        self.assertEqual(task.parameters["DB_LIST_CATEGORY"], "sales")

    def test_create_db_jmeter_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "db-api",
                "target_profile_id": "db-jmeter-crud-smoke",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "jmeter")
        self.assertEqual(task.script_path, "engines/jmeter/target_apps_db_flow_plan.jmx")
        self.assertEqual(task.target_url, "http://127.0.0.1:18089")
        self.assertEqual(task.parameters["FLOW_MODE"], "crud")
        self.assertEqual(task.parameters["DB_RECORD_NAME"], "smoke-record")

    def test_create_auth_refresh_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "auth-flow-api",
                "target_profile_id": "auth-k6-refresh-flow",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_auth_refresh_flow.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18086")
        self.assertEqual(task.parameters["ACCESS_TOKEN_USES"], "1")

    def test_create_auth_failure_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "auth-flow-api",
                "target_profile_id": "auth-k6-failure-branches",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_auth_refresh_flow.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18086")
        self.assertEqual(task.parameters["ASSERT_FAILURE_BRANCHES"], "1")

    def test_create_auth_checkout_jmeter_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "auth-flow-api",
                "target_profile_id": "auth-jmeter-checkout",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "jmeter")
        self.assertEqual(task.script_path, "engines/jmeter/target_apps_auth_flow_plan.jmx")
        self.assertEqual(task.parameters["FLOW_MODE"], "checkout")
        self.assertEqual(task.parameters["DEMO_SKU"], "sku-1")

    def test_create_auth_failure_jmeter_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "auth-flow-api",
                "target_profile_id": "auth-jmeter-failure-branches",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "jmeter")
        self.assertEqual(task.script_path, "engines/jmeter/target_apps_auth_flow_plan.jmx")
        self.assertEqual(task.parameters["FLOW_MODE"], "failure-branches")
        self.assertEqual(task.parameters["REFRESH_USES"], "1")

    def test_create_auth_session_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "auth-flow-api",
                "target_profile_id": "auth-k6-session-flow",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_auth_session_mfa_flow.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18086")
        self.assertEqual(task.parameters["FLOW_MODE"], "session")

    def test_create_auth_mfa_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "auth-flow-api",
                "target_profile_id": "auth-k6-mfa-flow",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "k6")
        self.assertEqual(task.script_path, "engines/k6/target_apps_auth_session_mfa_flow.js")
        self.assertEqual(task.target_url, "http://127.0.0.1:18086")
        self.assertEqual(task.parameters["FLOW_MODE"], "mfa")
        self.assertEqual(task.parameters["MFA_CHANNEL"], "sms")

    def test_create_auth_jmeter_task_from_template(self):
        response = self.client.post(
            "/api/tasks/",
            {
                "target_app_id": "auth-flow-api",
                "target_profile_id": "auth-jmeter-session-flow",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        task = LoadTestTask.objects.get(id=response.json()["id"])
        self.assertEqual(task.engine, "jmeter")
        self.assertEqual(task.script_path, "engines/jmeter/target_apps_auth_flow_plan.jmx")
        self.assertEqual(task.target_url, "http://127.0.0.1:18086")
        self.assertEqual(task.parameters["FLOW_MODE"], "session")
        self.assertEqual(task.parameters["SESSION_USES"], "2")
