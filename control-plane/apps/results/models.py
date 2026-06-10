"""
apps/results/models.py
======================
TestResult：儲存 Worker 回傳的完整壓測報表與解析後的摘要指標。
"""

import uuid

from django.db import models


class TestResult(models.Model):
    """
    每個 LoadTestTask 對應一筆 TestResult（OneToOne）。

    設計原則：
    - raw_report 儲存引擎原始輸出（k6 JSON Lines 結構化後 / JMeter JTL 轉換後），
      保留可重解析性，未來新增指標時無需重新壓測。
    - 摘要指標欄位化（avg/p90/p95/p99/throughput 等），
      允許 Django ORM 直接 filter/order_by，無需解析大型 JSON。
    """

    # ── 識別 ──────────────────────────────────────────────────────────
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    task = models.OneToOneField(
        "tasks.LoadTestTask",
        on_delete=models.CASCADE,
        related_name="result",
        help_text="一對一關聯至壓測任務",
    )

    # ── 原始報表 ────────────────────────────────────────────────────────
    raw_report = models.JSONField(
        help_text=(
            "引擎原始輸出（k6 --out json 解析後的結構化物件，"
            "或 JMeter JTL 轉換後的 JSON）。"
            "大型報表建議後續遷移至 FileField 或物件儲存（S3/GCS）。"
        )
    )

    # ── 解析後的摘要指標 ────────────────────────────────────────────────
    # 供 Dashboard 快速查詢，無需重新解析 raw_report
    total_requests = models.PositiveIntegerField(
        default=0,
        help_text="總請求數",
    )
    failed_requests = models.PositiveIntegerField(
        default=0,
        help_text="失敗請求數（HTTP 4xx/5xx 或 check 未通過）",
    )
    error_rate_pct = models.FloatField(
        default=0.0,
        help_text="失敗率百分比，e.g. 2.5 表示 2.5%",
    )
    avg_response_ms = models.FloatField(
        default=0.0,
        help_text="平均回應時間（毫秒）",
    )
    p90_response_ms = models.FloatField(
        default=0.0,
        help_text="P90 回應時間（毫秒）",
    )
    p95_response_ms = models.FloatField(
        default=0.0,
        help_text="P95 回應時間（毫秒）",
    )
    p99_response_ms = models.FloatField(
        default=0.0,
        help_text="P99 回應時間（毫秒）",
    )
    max_response_ms = models.FloatField(
        default=0.0,
        help_text="最大回應時間（毫秒）",
    )
    throughput_rps = models.FloatField(
        default=0.0,
        help_text="每秒請求數（requests/second）",
    )
    peak_vus = models.PositiveIntegerField(
        default=0,
        help_text="壓測期間的最大虛擬使用者數",
    )

    # ── Threshold 判定結果 ─────────────────────────────────────────────
    thresholds_passed = models.BooleanField(
        null=True,
        blank=True,
        help_text="整體 Threshold 是否全部通過；null 表示未設定 Thresholds",
    )
    # e.g. [{"metric": "p(95)<2000", "passed": false, "actual": 3340}]
    thresholds_detail = models.JSONField(
        default=list,
        blank=True,
        help_text="各 Threshold 詳細結果陣列",
    )

    # ── 稽核 ──────────────────────────────────────────────────────────
    collected_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Control Plane 收到 Worker 結果的時間",
    )

    class Meta:
        ordering        = ["-collected_at"]
        verbose_name    = "測試結果"
        verbose_name_plural = "測試結果"

    def __str__(self) -> str:
        passed = (
            "✅ PASSED" if self.thresholds_passed
            else ("❌ FAILED" if self.thresholds_passed is False else "—")
        )
        return f"Result for [{self.task}] {passed}"

    @property
    def success_rate_pct(self) -> float:
        """回傳成功率百分比（100 - error_rate_pct）。"""
        return round(100.0 - self.error_rate_pct, 4)
