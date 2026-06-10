"""
apps/workers/models.py
======================
WorkerNode：記錄遠端壓測節點的登記資料、狀態與心跳資訊。
"""

import uuid

from django.db import models
from django.utils import timezone
from datetime import timedelta


class WorkerNode(models.Model):
    """
    遠端 Worker Agent 的登記表。

    Worker 自我註冊後，Control Plane 依 status 與 capabilities
    選擇合適節點派發任務；Celery Beat 定期執行心跳巡邏，
    超過 30 秒無心跳的節點自動標記為 OFFLINE。
    """

    # ── 識別 ──────────────────────────────────────────────────────────
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="不可猜測的唯一識別碼（UUID4）",
    )
    name = models.CharField(
        max_length=128,
        unique=True,
        help_text="Worker 自報的唯一名稱，e.g. 'worker-taipei-01'",
    )
    ip_address = models.GenericIPAddressField(
        help_text="Worker 的可達 IP 位址（IPv4 或 IPv6）",
    )
    port = models.PositiveIntegerField(
        default=8100,
        help_text="Worker Agent 監聽的 Port",
    )

    # ── 狀態 ──────────────────────────────────────────────────────────
    class Status(models.TextChoices):
        ONLINE   = "online",   "在線可用"
        BUSY     = "busy",     "執行中"
        OFFLINE  = "offline",  "離線"
        DRAINING = "draining", "排水中（不接新任務）"

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OFFLINE,
        db_index=True,
        help_text="節點目前狀態",
    )

    # Worker 支援的引擎列表，e.g. ["k6", "jmeter"]
    capabilities = models.JSONField(
        default=list,
        blank=True,
        help_text="支援的壓測引擎清單，e.g. [\"k6\", \"jmeter\"]",
    )

    # ── 可觀測性 ──────────────────────────────────────────────────────
    last_heartbeat_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Worker 最後一次心跳的 UTC 時間",
    )
    # Worker 自報的資源快照，e.g. {"cpu_pct": 23.5, "mem_pct": 41.2}
    resource_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="最新資源使用率快照 {cpu_pct, mem_pct, disk_pct}",
    )
    active_task_count = models.PositiveIntegerField(
        default=0,
        help_text="目前正在執行的任務數量",
    )

    # ── 稽核 ──────────────────────────────────────────────────────────
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering        = ["-last_heartbeat_at"]
        verbose_name    = "Worker 節點"
        verbose_name_plural = "Worker 節點"

    def __str__(self) -> str:
        return f"{self.name} ({self.ip_address}:{self.port}) [{self.status}]"

    def is_alive(self, timeout_seconds: int = 30) -> bool:
        """
        判斷節點是否在 timeout_seconds 內有心跳。
        Celery Beat 的 mark_stale_workers 任務呼叫此方法。
        """
        if not self.last_heartbeat_at:
            return False
        return self.last_heartbeat_at >= timezone.now() - timedelta(seconds=timeout_seconds)
