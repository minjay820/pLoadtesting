"""
apps/tasks/models.py
====================
LoadTestTask：壓測任務主表，記錄從建立到完成的完整生命週期。
"""

import uuid

from django.db import models


class LoadTestTask(models.Model):
    """
    每筆記錄代表一次使用者發起的壓測任務。

    狀態機流程（7 態）：
        PENDING → SCHEDULED → DISPATCHED → RUNNING → COMPLETED
                                                    ↘ FAILED
        任意態 → CANCELLED（使用者主動取消）
    """

    # ── 識別 ──────────────────────────────────────────────────────────
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="任務唯一識別碼（UUID4）",
    )
    name = models.CharField(
        max_length=256,
        help_text="任務友善名稱，e.g. 'Sprint-42 壓測'",
    )

    # ── 引擎與腳本設定 ─────────────────────────────────────────────────
    class Engine(models.TextChoices):
        K6         = "k6",         "k6"
        JMETER     = "jmeter",     "JMeter"
        LOADRUNNER = "loadrunner", "LoadRunner"

    engine = models.CharField(
        max_length=16,
        choices=Engine.choices,
        db_index=True,
        help_text="使用的壓測引擎",
    )
    # 相對於 engines/ 目錄的腳本路徑，e.g. "k6/stress_cpu.js"
    script_path = models.CharField(
        max_length=512,
        help_text="腳本相對路徑，e.g. 'k6/stress_cpu.js'",
    )
    # 傳遞給引擎的額外參數，e.g. {"TARGET_URL": "http://...", "VUS": 50}
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="動態引擎參數字典，e.g. {\"TARGET_URL\": \"http://...\"}",
    )

    # ── 打擊目標 ───────────────────────────────────────────────────────
    target_url = models.URLField(
        max_length=512,
        help_text="靶機 Base URL，e.g. http://localhost:8000",
    )

    # ── 排程 ──────────────────────────────────────────────────────────
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="預計執行時間；null 表示立即執行",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Celery Worker 實際開始執行時間",
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="任務結束時間（成功或失敗）",
    )

    # ── 狀態機 ────────────────────────────────────────────────────────
    class Status(models.TextChoices):
        PENDING    = "pending",    "待派發"
        SCHEDULED  = "scheduled",  "已排程"
        DISPATCHED = "dispatched", "已派發至 Worker"
        RUNNING    = "running",    "執行中"
        COMPLETED  = "completed",  "已完成"
        FAILED     = "failed",     "失敗"
        CANCELLED  = "cancelled",  "已取消"

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="任務目前狀態（7 態狀態機）",
    )

    # 執行此任務的 Worker（任務完成後不刪除 FK，保留歷史紀錄）
    worker = models.ForeignKey(
        "workers.WorkerNode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
        help_text="執行節點；完成後保留歷史，不隨 Worker 刪除而消失",
    )

    # ── 失敗資訊 ───────────────────────────────────────────────────────
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="失敗原因摘要；成功時為空字串",
    )

    # ── 稽核 ──────────────────────────────────────────────────────────
    created_by = models.CharField(
        max_length=128,
        blank=True,
        help_text="建立者識別（Phase 3 MVP 先用字串，後續整合 Auth）",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering        = ["-created_at"]
        verbose_name    = "壓測任務"
        verbose_name_plural = "壓測任務"

    def __str__(self) -> str:
        return f"[{self.status}] {self.name} ({self.engine})"

    @property
    def duration_seconds(self) -> float | None:
        """計算任務實際執行秒數（finished_at - started_at）。"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
