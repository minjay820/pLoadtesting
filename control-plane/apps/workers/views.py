"""
apps/workers/views.py
======================
Workers API Views：

  WorkerListCreateView    GET  /api/workers/
                          POST /api/workers/       (Worker 自我註冊)

  WorkerHeartbeatView     POST /api/workers/{id}/heartbeat/
"""

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WorkerNode
from .serializers import (
    HeartbeatSerializer,
    WorkerNodeSerializer,
    WorkerRegistrationSerializer,
)


class WorkerListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/workers/  ─ 列出所有已註冊的 Worker 節點
    POST /api/workers/  ─ 新 Worker 自我註冊

    GET 回應：使用完整的 WorkerNodeSerializer（含 is_alive）。
    POST 請求：使用 WorkerRegistrationSerializer（僅接受 name/ip/port/capabilities）；
              若同名 Worker 已存在，更新其 ip_address、port、capabilities 並重設為 ONLINE。
    """

    queryset         = WorkerNode.objects.all()
    serializer_class = WorkerNodeSerializer  # 預設：GET 使用完整序列化

    def get_serializer_class(self):
        """依請求方法切換序列化器。"""
        if self.request.method == "POST":
            return WorkerRegistrationSerializer
        return WorkerNodeSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Worker 自我註冊。

        若同名節點已存在（Worker 重啟後重新上線），改為更新現有記錄
        而非建立重複資料，保留歷史任務關聯。
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"]
        existing = WorkerNode.objects.filter(name=name).first()

        if existing:
            # Worker 重啟場景：更新可變欄位，重設為 ONLINE
            for field in ("ip_address", "port", "capabilities"):
                if field in serializer.validated_data:
                    setattr(existing, field, serializer.validated_data[field])
            existing.status            = WorkerNode.Status.ONLINE
            existing.last_heartbeat_at = timezone.now()
            existing.active_task_count = 0
            existing.save()
            response_serializer = WorkerNodeSerializer(existing)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        # 首次註冊：建立新節點
        worker = serializer.save()
        response_serializer = WorkerNodeSerializer(worker)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class WorkerHeartbeatView(APIView):
    """
    POST /api/workers/{id}/heartbeat/

    供 Worker Agent 定期（每 10 秒）回報存活狀態。
    更新：
      - last_heartbeat_at → timezone.now()
      - status            → payload.status（預設 online）
      - active_task_count → payload.active_task_count（若提供）
      - resource_snapshot → payload.resource_snapshot（若提供）

    回傳：更新後的完整 WorkerNode 資料（HTTP 200）。
    若 Worker ID 不存在，回傳 HTTP 404。
    """

    def post(self, request: Request, pk: str) -> Response:
        try:
            worker = WorkerNode.objects.get(pk=pk)
        except WorkerNode.DoesNotExist:
            return Response(
                {"detail": f"Worker '{pk}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = HeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        # 必定更新的欄位
        worker.last_heartbeat_at = timezone.now()
        worker.status            = payload.get("status", WorkerNode.Status.ONLINE)

        # 選填更新的欄位
        if "active_task_count" in payload:
            worker.active_task_count = payload["active_task_count"]
        if "resource_snapshot" in payload:
            worker.resource_snapshot = payload["resource_snapshot"]

        worker.save(update_fields=[
            "last_heartbeat_at",
            "status",
            "active_task_count",
            "resource_snapshot",
            "updated_at",
        ])

        return Response(
            WorkerNodeSerializer(worker).data,
            status=status.HTTP_200_OK,
        )
