import json
import logging
import urllib.error
import urllib.request

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.workers.models import WorkerNode
from .models import LoadTestTask

logger = logging.getLogger(__name__)


def _worker_supports_engine(worker: WorkerNode, engine: str) -> bool:
    """Return True when the worker advertises support for the task engine."""
    return engine in (worker.capabilities or [])


def _select_available_worker(task: LoadTestTask) -> WorkerNode | None:
    """Pick an online, idle worker that supports the task engine."""
    candidates = WorkerNode.objects.filter(
        status=WorkerNode.Status.ONLINE,
        active_task_count=0,
    ).order_by("last_heartbeat_at")

    for worker in candidates:
        if _worker_supports_engine(worker, task.engine):
            return worker
    return None


def _dispatch_to_worker(task: LoadTestTask, worker: WorkerNode) -> None:
    """Send the task to the selected worker, raising on delivery failure."""
    worker_url = f"http://{worker.ip_address}:{worker.port}/execute"
    parameters = dict(task.parameters or {})
    if task.target_url:
        parameters.setdefault("TARGET_URL", task.target_url)

    payload = {
        "task_id": str(task.id),
        "engine": task.engine,
        "script_path": task.script_path,
        "parameters": parameters,
    }
    req = urllib.request.Request(
        worker_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-PLOADTESTING-API-TOKEN": settings.PLOADTESTING_API_TOKEN,
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=5) as response:
        if response.status < 200 or response.status >= 300:
            raise urllib.error.HTTPError(
                worker_url,
                response.status,
                f"Unexpected worker response: HTTP {response.status}",
                response.headers,
                None,
            )


@shared_task
def dispatch_pending_tasks():
    """
    Dispatch due pending tasks only after successful worker delivery.

    A task remains PENDING when no compatible idle worker exists or when HTTP
    delivery fails, so later scheduler ticks can retry it instead of leaving it
    permanently stuck in DISPATCHED.
    """
    now = timezone.now()

    pending_tasks = LoadTestTask.objects.filter(
        status=LoadTestTask.Status.PENDING
    ).filter(
        Q(scheduled_at__lte=now) | Q(scheduled_at__isnull=True)
    )

    dispatched_count = 0

    for task in pending_tasks:
        worker = _select_available_worker(task)
        if not worker:
            logger.warning("No compatible idle workers available for task %s", task.id)
            task.error_message = "No compatible idle worker is currently available."
            task.save(update_fields=["error_message", "updated_at"])
            continue

        logger.info("Dispatching task %s to worker %s", task.id, worker.name)
        try:
            _dispatch_to_worker(task, worker)
        except Exception as exc:  # noqa: BLE001 - keep scheduler resilient
            logger.error("Failed to dispatch task %s to worker %s: %s", task.id, worker.name, exc)
            task.error_message = f"Dispatch to worker '{worker.name}' failed: {exc}"
            task.save(update_fields=["error_message", "updated_at"])
            continue

        task.worker = worker
        task.status = LoadTestTask.Status.DISPATCHED
        task.error_message = ""
        task.save(update_fields=["worker", "status", "error_message", "updated_at"])
        dispatched_count += 1
        logger.info("Successfully dispatched task %s to worker %s", task.id, worker.name)

    return dispatched_count
