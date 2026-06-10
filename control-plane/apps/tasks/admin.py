from django.contrib import admin

from .models import LoadTestTask


@admin.register(LoadTestTask)
class LoadTestTaskAdmin(admin.ModelAdmin):
    list_display = (
        "name", "engine", "status", "worker",
        "scheduled_at", "started_at", "finished_at", "created_at",
    )
    list_filter   = ("status", "engine")
    search_fields = ("name", "target_url", "created_by")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering      = ("-created_at",)
    autocomplete_fields = []

    fieldsets = (
        ("基本資訊", {
            "fields": ("id", "name", "created_by"),
        }),
        ("引擎設定", {
            "fields": ("engine", "script_path", "parameters", "target_url"),
        }),
        ("排程與時序", {
            "fields": ("scheduled_at", "started_at", "finished_at"),
        }),
        ("狀態與派發", {
            "fields": ("status", "worker", "error_message"),
        }),
        ("稽核", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
