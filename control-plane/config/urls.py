"""
URL configuration for nebula-load-tester Control Plane.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),

    # API v1
    # 所有 /api/ 路徑由各 app 的 urls.py 負責，
    # 未來新增 tasks、results app 時直接在此 include。
    path("api/workers/", include("apps.workers.urls", namespace="workers")),
]

