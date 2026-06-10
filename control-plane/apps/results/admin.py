from django.contrib import admin

from .models import TestResult


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = (
        "task", "thresholds_passed",
        "total_requests", "failed_requests", "error_rate_pct",
        "avg_response_ms", "p95_response_ms", "throughput_rps",
        "collected_at",
    )
    list_filter   = ("thresholds_passed",)
    search_fields = ("task__name",)
    readonly_fields = ("id", "collected_at")
    ordering      = ("-collected_at",)

    fieldsets = (
        ("關聯任務", {
            "fields": ("id", "task"),
        }),
        ("回應時間指標 (ms)", {
            "fields": (
                "avg_response_ms", "p90_response_ms",
                "p95_response_ms", "p99_response_ms", "max_response_ms",
            ),
        }),
        ("流量指標", {
            "fields": (
                "total_requests", "failed_requests",
                "error_rate_pct", "throughput_rps", "peak_vus",
            ),
        }),
        ("Threshold 判定", {
            "fields": ("thresholds_passed", "thresholds_detail"),
        }),
        ("原始報表", {
            "fields": ("raw_report",),
            "classes": ("collapse",),
            "description": "引擎完整原始輸出（展開可查看，通常資料量較大）",
        }),
        ("稽核", {
            "fields": ("collected_at",),
            "classes": ("collapse",),
        }),
    )
