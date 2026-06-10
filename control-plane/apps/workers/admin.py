from django.contrib import admin

from .models import WorkerNode


@admin.register(WorkerNode)
class WorkerNodeAdmin(admin.ModelAdmin):
    list_display = (
        "name", "ip_address", "port", "status",
        "active_task_count", "last_heartbeat_at", "registered_at",
    )
    list_filter    = ("status",)
    search_fields  = ("name", "ip_address")
    readonly_fields = ("id", "registered_at", "updated_at")
    ordering       = ("-last_heartbeat_at",)

    fieldsets = (
        ("識別資訊", {
            "fields": ("id", "name", "ip_address", "port"),
        }),
        ("狀態與能力", {
            "fields": ("status", "capabilities", "active_task_count"),
        }),
        ("可觀測性", {
            "fields": ("last_heartbeat_at", "resource_snapshot"),
        }),
        ("稽核", {
            "fields": ("registered_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
