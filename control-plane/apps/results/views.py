"""
apps/results/views.py
======================
Results API Views：

  TaskResultCreateView   POST /api/tasks/{task_id}/results/
    ─ 專供 Worker 執行完畢後回傳測試報告。
    ─ 建立 TestResult 後，連動更新 LoadTestTask：
        status    → COMPLETED
        finished_at → timezone.now()
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tasks.models import LoadTestTask
from .models import TestResult
from .serializers import TestResultCreateSerializer, TestResultSerializer


class TaskResultCreateView(APIView):
    """
    POST /api/tasks/{task_id}/results/

    Worker 執行引擎完畢後呼叫此端點，傳入：
      - raw_report         (必填) 引擎完整原始輸出
      - 各摘要指標欄位      (選填，有預設值)

    成功後：
      1. 建立 TestResult 記錄（task 由 URL task_id 注入）
      2. 連動更新 LoadTestTask.status → COMPLETED
      3. 連動更新 LoadTestTask.finished_at → now()
      4. 回傳完整 TestResult 資料（HTTP 201）

    錯誤情境：
      - task_id 不存在              → 404
      - 該任務已有 Result（重複提交） → 409 Conflict
      - payload 驗證失敗             → 400
    """

    def post(self, request: Request, task_id: str) -> Response:
        # ── 查找對應任務 ───────────────────────────────────────────
        try:
            task = LoadTestTask.objects.get(pk=task_id)
        except LoadTestTask.DoesNotExist:
            return Response(
                {"detail": f"Task '{task_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── 防止重複提交 ────────────────────────────────────────────
        if hasattr(task, "result"):
            return Response(
                {"detail": "A result already exists for this task."},
                status=status.HTTP_409_CONFLICT,
            )

        # ── 驗證 Worker 傳入的 payload ──────────────────────────────
        serializer = TestResultCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        execution_status = serializer.validated_data.pop("execution_status", "completed")
        error_message = serializer.validated_data.pop("error_message", "")

        # ── 建立 TestResult（task 由此注入，不來自請求端） ──────────
        result = TestResult.objects.create(task=task, **serializer.validated_data)

        # ── 連動更新 LoadTestTask 狀態 ──────────────────────────────
        task.status = (
            LoadTestTask.Status.FAILED
            if execution_status == "failed"
            else LoadTestTask.Status.COMPLETED
        )
        task.error_message = error_message if execution_status == "failed" else ""
        task.finished_at = timezone.now()
        task.save(update_fields=["status", "error_message", "finished_at", "updated_at"])

        return Response(
            TestResultSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )
