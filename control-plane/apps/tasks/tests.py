from unittest import mock
from urllib.error import URLError

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.results.models import TestResult
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
class TaskTemplateApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_X_PLOADTESTING_API_TOKEN=API_TOKEN)

    def test_list_task_templates(self):
        response = self.client.get("/api/tasks/templates/")

        self.assertEqual(response.status_code, 200)
        templates = response.json()["templates"]
        self.assertTrue(any(row["target_profile_id"] == "echo-k6-smoke" for row in templates))
        self.assertTrue(any(row["target_profile_id"] == "payload-jmeter-download" for row in templates))
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
        self.assertIsNone(templates_by_profile["payload-jmeter-download"]["equivalent_profile_id"])

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
