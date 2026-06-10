"""
apps/workers/urls.py
====================
Workers app 的路由設定。
"""

from django.urls import path

from .views import WorkerHeartbeatView, WorkerListCreateView

app_name = "workers"

urlpatterns = [
    # GET  /api/workers/         — 列出所有 Worker
    # POST /api/workers/         — Worker 自我註冊
    path("", WorkerListCreateView.as_view(), name="worker-list-create"),

    # POST /api/workers/<uuid:pk>/heartbeat/  — Worker 心跳回報
    path("<uuid:pk>/heartbeat/", WorkerHeartbeatView.as_view(), name="worker-heartbeat"),
]
