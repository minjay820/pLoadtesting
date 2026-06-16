"""
apps/tasks/urls.py
==================
Tasks app 的路由設定。
"""

from django.urls import path

from .views import (
    TaskArtifactsView,
    TaskDetailView,
    TaskListCreateView,
    TaskResultSummaryView,
    TaskShardPlanView,
    TaskTemplateCoverageView,
    TaskTemplateListView,
)

app_name = "tasks"

urlpatterns = [
    path("templates/coverage/", TaskTemplateCoverageView.as_view(), name="task-template-coverage"),
    path("templates/", TaskTemplateListView.as_view(), name="task-template-list"),

    # GET  /api/tasks/         — 列出所有任務
    # POST /api/tasks/         — 建立新壓測任務
    path("", TaskListCreateView.as_view(), name="task-list-create"),

    # GET  /api/tasks/<uuid:pk>/  — 查詢單一任務（含巢狀 result）
    path("<uuid:pk>/result-summary/", TaskResultSummaryView.as_view(), name="task-result-summary"),
    path("<uuid:pk>/artifacts/", TaskArtifactsView.as_view(), name="task-artifacts"),
    path("<uuid:pk>/shard-plan/", TaskShardPlanView.as_view(), name="task-shard-plan"),
    path("<uuid:pk>/", TaskDetailView.as_view(), name="task-detail"),
]
