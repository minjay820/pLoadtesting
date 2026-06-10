import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import WorkerNode

logger = logging.getLogger(__name__)

@shared_task
def mark_stale_workers():
    """
    定期巡邏，將超過 30 秒沒有收到心跳的 Worker 狀態標記為 OFFLINE。
    """
    timeout_threshold = timezone.now() - timedelta(seconds=30)
    
    # 尋找目前狀態不是 OFFLINE，且最後心跳時間早於閾值的 Worker
    stale_workers = WorkerNode.objects.exclude(status=WorkerNode.Status.OFFLINE).filter(
        last_heartbeat_at__lt=timeout_threshold
    )
    
    count = stale_workers.count()
    if count > 0:
        logger.info(f"Marking {count} stale workers as OFFLINE")
        stale_workers.update(status=WorkerNode.Status.OFFLINE)
    
    return count
