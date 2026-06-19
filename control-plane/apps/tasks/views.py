"""
apps/tasks/views.py
====================
Tasks API Views：

  TaskListCreateView   GET  /api/tasks/       ─ 列出所有任務
                       POST /api/tasks/       ─ 建立壓測任務（status 強制 pending）

  TaskDetailView       GET  /api/tasks/{id}/  ─ 查詢單一任務詳情（含巢狀 result）
"""

from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import has_shared_api_token

from .models import LoadTestTask
from .read_models import (
    artifact_download_placeholder_read_model,
    artifact_metadata_read_model,
    artifact_not_found_read_model,
    result_summary_read_model,
    task_detail_read_model,
    task_history_item,
)
from .serializers import LoadTestTaskCreateSerializer, LoadTestTaskSerializer
from .template_registry import get_task_template, get_template_coverage_export, list_task_templates


DEMO_TASK_OPERATION_MODE = "deployment_smoke"
SAFE_DEMO_TARGET_APP_ID = "echo-api"
SAFE_DEMO_PROFILE_IDS = {"echo-k6-smoke", "echo-jmeter-smoke"}
ALLOWED_DEMO_CREATE_FIELDS = {"target_app_id", "target_profile_id", "name", "created_by"}
MAX_DEMO_DURATION_SECONDS = 30
MAX_DEMO_RUN_SECONDS = 60


def _access_denied() -> Response:
    return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)


def _demo_task_api_enabled() -> bool:
    return bool(getattr(settings, "PLOADTESTING_ENABLE_DEMO_TASK_API", False))


def _is_safe_demo_profile(target_app_id: str | None, target_profile_id: str | None) -> bool:
    return target_app_id == SAFE_DEMO_TARGET_APP_ID and target_profile_id in SAFE_DEMO_PROFILE_IDS


def _demo_create_payload_allowed(data) -> bool:  # noqa: ANN001 - request.data can be several mapping types
    if not hasattr(data, "keys"):
        return False
    keys = set(data.keys())
    if not keys or keys - ALLOWED_DEMO_CREATE_FIELDS:
        return False
    return _is_safe_demo_profile(data.get("target_app_id"), data.get("target_profile_id"))


def _execution_within_demo_bounds(execution: dict) -> bool:
    try:
        duration_seconds = int(execution.get("duration_seconds"))
        max_run_seconds = int(execution.get("max_run_seconds"))
    except (TypeError, ValueError):
        return False
    return duration_seconds <= MAX_DEMO_DURATION_SECONDS and max_run_seconds <= MAX_DEMO_RUN_SECONDS


def _validated_demo_data_is_safe(validated_data: dict) -> bool:
    target_app_id = validated_data.get("_target_app_id")
    target_profile_id = validated_data.get("_target_profile_id")
    if not _is_safe_demo_profile(target_app_id, target_profile_id):
        return False

    try:
        template = get_task_template(target_app_id, target_profile_id)
    except ValueError:
        return False

    parameters = validated_data.get("parameters") if isinstance(validated_data.get("parameters"), dict) else {}
    execution = parameters.get("execution") if isinstance(parameters.get("execution"), dict) else {}
    return (
        validated_data.get("target_url") == template["target_url"]
        and validated_data.get("script_path") == template["script_path"]
        and validated_data.get("engine") == template["engine"]
        and _execution_within_demo_bounds(execution)
    )


def _mark_demo_task(task: LoadTestTask) -> None:
    parameters = dict(task.parameters or {})
    parameters["task_operation_mode"] = DEMO_TASK_OPERATION_MODE
    task.parameters = parameters
    task.save(update_fields=["parameters", "updated_at"])


def _is_safe_demo_task(task: LoadTestTask) -> bool:
    parameters = task.parameters if isinstance(task.parameters, dict) else {}
    if parameters.get("task_operation_mode") != DEMO_TASK_OPERATION_MODE:
        return False

    target_app_id = parameters.get("target_app_id")
    target_profile_id = parameters.get("target_profile_id")
    if not _is_safe_demo_profile(target_app_id, target_profile_id):
        return False

    try:
        template = get_task_template(target_app_id, target_profile_id)
    except ValueError:
        return False

    execution = parameters.get("execution") if isinstance(parameters.get("execution"), dict) else {}
    return (
        task.target_url == template["target_url"]
        and task.script_path == template["script_path"]
        and task.engine == template["engine"]
        and _execution_within_demo_bounds(execution)
    )


def _can_read_demo_task(request: Request, task: LoadTestTask) -> bool:
    return has_shared_api_token(request) or (_demo_task_api_enabled() and _is_safe_demo_task(task))


def _demo_task_queryset(queryset):
    return queryset.filter(
        parameters__task_operation_mode=DEMO_TASK_OPERATION_MODE,
        parameters__target_app_id=SAFE_DEMO_TARGET_APP_ID,
        parameters__target_profile_id__in=sorted(SAFE_DEMO_PROFILE_IDS),
    )


class TaskListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/tasks/  ─ 列出所有任務（最新建立在前）
    POST /api/tasks/  ─ 建立新壓測任務

    - GET：回傳 external-client-friendly run history read model。
    - POST：使用 LoadTestTaskCreateSerializer，status 強制為 PENDING，
            回應切回完整序列化器，讓呼叫端立即得到任務 ID 與完整狀態。
    """

    queryset = LoadTestTask.objects.select_related("worker", "result").all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return LoadTestTaskCreateSerializer
        return LoadTestTaskSerializer

    def list(self, request: Request, *args, **kwargs) -> Response:
        shared_access = has_shared_api_token(request)
        if not shared_access and not _demo_task_api_enabled():
            return _access_denied()

        queryset = self.get_queryset()
        demo_read = not shared_access
        if demo_read:
            queryset = _demo_task_queryset(queryset)
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        try:
            limit = int(request.query_params.get("limit", "20"))
        except ValueError:
            limit = 20
        limit = max(1, min(limit, 20 if demo_read else 100))
        tasks = list(queryset[:limit])
        if demo_read:
            tasks = [task for task in tasks if _is_safe_demo_task(task)]
        return Response(
            {
                "source": {"status": "ok"},
                "summary": {
                    "count": len(tasks),
                    "limit": limit,
                    "total_available": queryset.count(),
                },
                "items": [task_history_item(task) for task in tasks],
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        demo_create = False
        if not has_shared_api_token(request):
            if not _demo_task_api_enabled() or not _demo_create_payload_allowed(request.data):
                return _access_denied()
            demo_create = True

        create_serializer = LoadTestTaskCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        if demo_create and not _validated_demo_data_is_safe(create_serializer.validated_data):
            return _access_denied()
        task = create_serializer.save()
        if demo_create:
            _mark_demo_task(task)

        # 回傳完整序列化（含 status、id、result 等唯讀欄位）
        read_serializer = LoadTestTaskSerializer(task)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    """
    GET /api/tasks/{id}/  ─ 查詢單一任務詳情

    使用 select_related 避免 N+1：
      - worker：WorkerNode
      - result：TestResult（OneToOne）
    任務未完成時 result 欄位為 null。
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, pk: str) -> Response:
        try:
            task = LoadTestTask.objects.select_related("worker", "result").get(pk=pk)
        except LoadTestTask.DoesNotExist:
            return Response({"detail": f"Task '{pk}' not found."}, status=status.HTTP_404_NOT_FOUND)
        if not _can_read_demo_task(request, task):
            return _access_denied()
        return Response(task_detail_read_model(task), status=status.HTTP_200_OK)


class TaskTemplateListView(APIView):
    """
    GET /api/tasks/templates/  ─ 列出可供 manifest-driven 建立流程使用的 task templates
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"templates": list_task_templates()}, status=status.HTTP_200_OK)


class TaskTemplateCoverageView(APIView):
    """
    GET /api/tasks/templates/coverage/  ─ machine-readable target profile coverage export
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(get_template_coverage_export(), status=status.HTTP_200_OK)


class TaskShardPlanView(APIView):
    """
    GET /api/tasks/{id}/shard-plan/ returns the stored manual shard execution plan.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, pk: str) -> Response:
        try:
            task = LoadTestTask.objects.get(pk=pk)
        except LoadTestTask.DoesNotExist:
            return Response({"detail": f"Task '{pk}' not found."}, status=status.HTTP_404_NOT_FOUND)
        if not _can_read_demo_task(request, task):
            return _access_denied()

        plan = (task.parameters or {}).get("shard_execution_plan")
        if not plan:
            return Response({"detail": "No shard execution plan exists for this task."}, status=status.HTTP_404_NOT_FOUND)
        return Response(plan, status=status.HTTP_200_OK)


class TaskResultSummaryView(APIView):
    """
    GET /api/tasks/{id}/result-summary/ returns a safe result summary read contract.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, pk: str) -> Response:
        try:
            task = LoadTestTask.objects.select_related("result").get(pk=pk)
        except LoadTestTask.DoesNotExist:
            return Response({"detail": f"Task '{pk}' not found."}, status=status.HTTP_404_NOT_FOUND)
        if not _can_read_demo_task(request, task):
            return _access_denied()
        return Response(result_summary_read_model(task), status=status.HTTP_200_OK)


class TaskArtifactsView(APIView):
    """
    GET /api/tasks/{id}/artifacts/ returns artifact metadata placeholder contract.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, pk: str) -> Response:
        try:
            task = LoadTestTask.objects.prefetch_related("artifacts").get(pk=pk)
        except LoadTestTask.DoesNotExist:
            return Response({"detail": f"Task '{pk}' not found."}, status=status.HTTP_404_NOT_FOUND)
        if not _can_read_demo_task(request, task):
            return _access_denied()
        return Response(artifact_metadata_read_model(task), status=status.HTTP_200_OK)


class TaskArtifactDownloadView(APIView):
    """
    GET /api/tasks/{id}/artifacts/{artifact_id}/download/ returns a structured not-implemented response.
    """

    def get(self, request: Request, pk: str, artifact_id: str) -> Response:
        try:
            task = LoadTestTask.objects.prefetch_related("artifacts").get(pk=pk)
        except LoadTestTask.DoesNotExist:
            return Response({"detail": f"Task '{pk}' not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = artifact_download_placeholder_read_model(task, artifact_id)
        if payload is None:
            return Response(
                artifact_not_found_read_model(task, artifact_id),
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            payload,
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
