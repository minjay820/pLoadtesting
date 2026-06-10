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
