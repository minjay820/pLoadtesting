"""
apps/workers/serializers.py
============================
WorkerNode 的序列化器，包含：
  - WorkerNodeSerializer：完整欄位讀寫
  - WorkerRegistrationSerializer：僅接收必要的自我註冊欄位
  - HeartbeatSerializer：驗證心跳 payload
"""

from django.utils import timezone
from rest_framework import serializers

from .models import WorkerNode


class WorkerNodeSerializer(serializers.ModelSerializer):
    """
    完整的 WorkerNode 序列化器（用於 GET 回應）。

    `is_alive` 為唯讀計算欄位，由 `is_alive()` 方法衍生，
    讓 API 消費者不需自行計算心跳超時。
    """

    # 唯讀計算欄位：30 秒內有心跳視為存活
    is_alive = serializers.SerializerMethodField()

    class Meta:
        model  = WorkerNode
        fields = [
            "id",
            "name",
            "ip_address",
            "port",
            "status",
            "capabilities",
            "last_heartbeat_at",
            "resource_snapshot",
            "active_task_count",
            "is_alive",
            "registered_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_alive",
            "registered_at",
            "updated_at",
        ]

    def get_is_alive(self, obj: WorkerNode) -> bool:
        return obj.is_alive()


class WorkerRegistrationSerializer(serializers.ModelSerializer):
    """
    Worker 自我註冊時使用的序列化器。

    只接受 Worker 自行提供的欄位；status 固定為 ONLINE，
    last_heartbeat_at 由 View 設為 now()。
    """

    name = serializers.CharField(validators=[])

    class Meta:
        model  = WorkerNode
        fields = ["name", "ip_address", "port", "capabilities"]
        extra_kwargs = {
            "port":         {"required": False},
            "capabilities": {"required": False},
        }

    def create(self, validated_data: dict) -> WorkerNode:
        """建立節點時自動設定初始狀態與首次心跳時間。"""
        validated_data["status"]            = WorkerNode.Status.ONLINE
        validated_data["last_heartbeat_at"] = timezone.now()
        return super().create(validated_data)


class HeartbeatSerializer(serializers.Serializer):
    """
    Worker 心跳 payload 的驗證器。

    所有欄位均為選填：Worker 可僅傳送 status，
    也可附帶完整的資源快照資訊。
    """

    status = serializers.ChoiceField(
        choices=WorkerNode.Status.choices,
        required=False,
        default=WorkerNode.Status.ONLINE,
        help_text="Worker 目前狀態，預設 online",
    )
    active_task_count = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="目前正在執行的任務數量",
    )
    resource_snapshot = serializers.DictField(
        required=False,
        help_text="資源使用率快照，e.g. {cpu_pct: 23.5, mem_pct: 41.2}",
    )
