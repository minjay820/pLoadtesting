import os
from celery import Celery
from celery.schedules import crontab

# 設置 Django 默認的 settings 模組
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('nebula_control_plane')

# 從 Django 的 settings 中讀取配置，所有 Celery 相關的設定鍵值都要以 CELERY_ 開頭
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自動從所有已安裝的 apps 中加載任務
app.autodiscover_tasks()

# Celery Beat 排程設定
app.conf.beat_schedule = {
    'mark-stale-workers-every-60-seconds': {
        'task': 'apps.workers.tasks.mark_stale_workers',
        'schedule': 60.0,
    },
    'dispatch-pending-tasks-every-10-seconds': {
        'task': 'apps.tasks.tasks.dispatch_pending_tasks',
        'schedule': 10.0,
    },
}
