"""
URL configuration for pLoadtesting Control Plane.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # ── API v1 ─────────────────────────────────────────────────────────────
    # Workers：節點登記 / 心跳
    path("api/workers/", include("apps.workers.urls", namespace="workers")),

    # Tasks：任務建立 / 查詢
    path("api/tasks/",   include("apps.tasks.urls",   namespace="tasks")),

    # Results：Worker 回傳報告（路由格式 /api/tasks/<uuid>/results/）
    path("api/tasks/",   include("apps.results.urls",  namespace="results")),
]


