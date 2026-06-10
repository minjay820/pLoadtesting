"""
apps/tasks/serializers.py
==========================
LoadTestTask 的序列化器：

  LoadTestTaskSerializer        ─ 完整讀（含巢狀 result）
  LoadTestTaskCreateSerializer  ─ 建立任務時使用，強制 status=pending
"""

from rest_framework import serializers

from apps.results.serializers import TestResultSerializer
from .models import LoadTestTask


class LoadTestTaskSerializer(serializers.ModelSerializer):
    """
    完整的 LoadTestTask 序列化器（GET 回應使用）。

    巢狀嵌入 result：任務尚未完成則為 null，
    完成後帶出所有 TestResult 欄位（含摘要指標）。
    duration_seconds 為唯讀計算屬性（Model property）。
    """

    # 唯讀巢狀序列化：來自 TestResult.task OneToOne related_name="result"
    result = TestResultSerializer(read_only=True, allow_null=True, default=None)

    # 唯讀計算屬性：started_at → finished_at 秒差
    duration_seconds = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model  = LoadTestTask
        fields = [
            "id",
            "name",
            "engine",
            "script_path",
            "parameters",
            "target_url",
            "scheduled_at",
            "started_at",
            "finished_at",
            "duration_seconds",
            "status",
            "worker",
            "error_message",
            "created_by",
            "created_at",
            "updated_at",
            "result",
        ]
        read_only_fields = [
            "id",
            "status",
            "started_at",
            "finished_at",
            "duration_seconds",
            "created_at",
            "updated_at",
            "result",
        ]


class LoadTestTaskCreateSerializer(serializers.ModelSerializer):
    """
    建立任務時使用的序列化器。

    status 強制鎖定為 PENDING，worker / started_at / finished_at
    均不在此設定（由 Control Plane 生命週期管理）。
    """

    class Meta:
        model  = LoadTestTask
        fields = [
            "name",
            "engine",
            "script_path",
            "parameters",
            "target_url",
            "scheduled_at",
            "created_by",
        ]
        extra_kwargs = {
            "parameters":   {"required": False},
            "scheduled_at": {"required": False},
            "created_by":   {"required": False},
        }

    def create(self, validated_data: dict) -> LoadTestTask:
        """強制 status=PENDING，確保狀態機從正確起點出發。"""
        validated_data["status"] = LoadTestTask.Status.PENDING
        return super().create(validated_data)
