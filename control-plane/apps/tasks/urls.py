"""
apps/tasks/urls.py
==================
Tasks app 的路由設定。
"""

from django.urls import path

from .views import TaskDetailView, TaskListCreateView

app_name = "tasks"

urlpatterns = [
    # GET  /api/tasks/         — 列出所有任務
    # POST /api/tasks/         — 建立新壓測任務
    path("", TaskListCreateView.as_view(), name="task-list-create"),

    # GET  /api/tasks/<uuid:pk>/  — 查詢單一任務（含巢狀 result）
    path("<uuid:pk>/", TaskDetailView.as_view(), name="task-detail"),
]
