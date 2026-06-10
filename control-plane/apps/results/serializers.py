"""
apps/results/serializers.py
============================
TestResult 的序列化器。

不引用 tasks 模組，避免循環依賴：
  tasks.serializers → results.serializers  ✅
  results.serializers → tasks.serializers  ❌（禁止）
"""

from rest_framework import serializers

from .models import TestResult


class TestResultSerializer(serializers.ModelSerializer):
    """
    完整的 TestResult 序列化器。

    - GET（巢狀於 LoadTestTaskSerializer）：read_only 展示所有指標欄位。
    - POST /api/tasks/{task_id}/results/（Worker 回傳結果）：
        接受 raw_report + 所有摘要指標，task 欄位由 View 注入，
        不由請求端傳入（避免 task_id 被偽造）。
    """

    class Meta:
        model  = TestResult
        fields = [
            "id",
            "task",
            # 原始報表
            "raw_report",
            # 流量指標
            "total_requests",
            "failed_requests",
            "error_rate_pct",
            # 回應時間指標
            "avg_response_ms",
            "p90_response_ms",
            "p95_response_ms",
            "p99_response_ms",
            "max_response_ms",
            # 吞吐量 / 並發
            "throughput_rps",
            "peak_vus",
            # Threshold 判定
            "thresholds_passed",
            "thresholds_detail",
            # 稽核
            "collected_at",
        ]
        read_only_fields = ["id", "task", "collected_at"]


class TestResultCreateSerializer(serializers.ModelSerializer):
    execution_status = serializers.ChoiceField(
        choices=["completed", "failed"],
        required=False,
        default="completed",
        write_only=True,
        help_text="Worker execution status for the task lifecycle.",
    )
    error_message = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="Failure summary when execution_status is failed.",
    )

    """
    Worker 回傳結果時使用的序列化器。

    - task 欄位被排除在外（由 View 透過 URL 的 task_id 注入）。
    - raw_report 為必填；所有摘要指標均有預設值，允許 Worker
      只傳送部分指標（例如僅有 k6 subset 的情境）。
    """

    class Meta:
        model  = TestResult
        fields = [
            "raw_report",
            "total_requests",
            "failed_requests",
            "error_rate_pct",
            "avg_response_ms",
            "p90_response_ms",
            "p95_response_ms",
            "p99_response_ms",
            "max_response_ms",
            "throughput_rps",
            "peak_vus",
            "thresholds_passed",
            "thresholds_detail",
            "execution_status",
            "error_message",
        ]
        extra_kwargs = {
            "raw_report":       {"required": True},
            "total_requests":   {"required": False},
            "failed_requests":  {"required": False},
            "error_rate_pct":   {"required": False},
            "avg_response_ms":  {"required": False},
            "p90_response_ms":  {"required": False},
            "p95_response_ms":  {"required": False},
            "p99_response_ms":  {"required": False},
            "max_response_ms":  {"required": False},
            "throughput_rps":   {"required": False},
            "peak_vus":         {"required": False},
            "thresholds_passed":{"required": False},
            "thresholds_detail":{"required": False},
        }
