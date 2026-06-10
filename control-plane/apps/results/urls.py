"""
apps/results/urls.py
====================
Results app 的路由設定。

路徑掛在 /api/tasks/<uuid>/results/ 下，
語意上清楚表達「某任務的結果」，符合 REST 資源從屬關係。
"""

from django.urls import path

from .views import TaskResultCreateView

app_name = "results"

urlpatterns = [
    # POST /api/tasks/<uuid:task_id>/results/  — Worker 回傳測試報告
    path(
        "<uuid:task_id>/results/",
        TaskResultCreateView.as_view(),
        name="task-result-create",
    ),
]
