"""
apps/tasks/views.py
====================
Tasks API Views：

  TaskListCreateView   GET  /api/tasks/       ─ 列出所有任務
                       POST /api/tasks/       ─ 建立壓測任務（status 強制 pending）

  TaskDetailView       GET  /api/tasks/{id}/  ─ 查詢單一任務詳情（含巢狀 result）
"""

from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LoadTestTask
from .serializers import LoadTestTaskCreateSerializer, LoadTestTaskSerializer
from .template_registry import get_template_coverage_export, list_task_templates


class TaskListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/tasks/  ─ 列出所有任務（最新建立在前）
    POST /api/tasks/  ─ 建立新壓測任務

    - GET：使用 LoadTestTaskSerializer（含巢狀 result）。
    - POST：使用 LoadTestTaskCreateSerializer，status 強制為 PENDING，
            回應切回完整序列化器，讓呼叫端立即得到任務 ID 與完整狀態。
    """

    queryset = LoadTestTask.objects.select_related("worker", "result").all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return LoadTestTaskCreateSerializer
        return LoadTestTaskSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        create_serializer = LoadTestTaskCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        task = create_serializer.save()

        # 回傳完整序列化（含 status、id、result 等唯讀欄位）
        read_serializer = LoadTestTaskSerializer(task)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class TaskDetailView(generics.RetrieveAPIView):
    """
    GET /api/tasks/{id}/  ─ 查詢單一任務詳情

    使用 select_related 避免 N+1：
      - worker：WorkerNode
      - result：TestResult（OneToOne）
    任務未完成時 result 欄位為 null。
    """

    queryset         = LoadTestTask.objects.select_related("worker", "result").all()
    serializer_class = LoadTestTaskSerializer
    lookup_field     = "pk"


class TaskTemplateListView(APIView):
    """
    GET /api/tasks/templates/  ─ 列出可供 manifest-driven 建立流程使用的 task templates
    """

    def get(self, request: Request) -> Response:
        return Response({"templates": list_task_templates()}, status=status.HTTP_200_OK)


class TaskTemplateCoverageView(APIView):
    """
    GET /api/tasks/templates/coverage/  ─ machine-readable target profile coverage export
    """

    def get(self, request: Request) -> Response:
        return Response(get_template_coverage_export(), status=status.HTTP_200_OK)
