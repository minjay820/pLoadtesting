import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from .models import LoadTestTask
from apps.workers.models import WorkerNode

logger = logging.getLogger(__name__)

@shared_task
def dispatch_pending_tasks():
    """
    尋找 status='pending' 且 scheduled_at 小於等於現在時間 (或為 null) 的任務。
    尋找 status='online' 的 Worker。
    如果找到 Worker，將任務的 worker 欄位指派給它，並將狀態改為 dispatched。
    """
    now = timezone.now()
    
    # 尋找需要執行的任務 (排程時間到了或未設定)
    pending_tasks = LoadTestTask.objects.filter(
        status=LoadTestTask.Status.PENDING
    ).filter(
        Q(scheduled_at__lte=now) | Q(scheduled_at__isnull=True)
    )
    
    if not pending_tasks.exists():
        return 0
        
    dispatched_count = 0
    
    for task in pending_tasks:
        # 簡單的調度邏輯：找到一個 online 且支援該任務引擎的 Worker
        # 目前 MVP 階段，只要是 online 即可
        worker = WorkerNode.objects.filter(status=WorkerNode.Status.ONLINE).first()
        
        if worker:
            logger.info(f"Dispatching task {task.id} to worker {worker.name}")
            task.worker = worker
            task.status = LoadTestTask.Status.DISPATCHED
            task.save(update_fields=['worker', 'status', 'updated_at'])
            dispatched_count += 1
            
            # Send HTTP request to worker
            worker_url = f"http://{worker.ip_address}:{worker.port}/execute"
            payload = {
                "task_id": str(task.id),
                "engine": task.engine,
                "script_path": task.script_path,
                "parameters": task.parameters or {}
            }
            try:
                import urllib.request
                import json
                
                # Add target_url to parameters if not present
                if task.target_url:
                    payload["parameters"]["TARGET_URL"] = task.target_url
                
                req = urllib.request.Request(
                    worker_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status >= 400:
                        raise Exception(f"HTTP Error {response.status}")
                logger.info(f"Successfully dispatched task {task.id} to worker {worker.name}")
            except Exception as e:
                logger.error(f"Failed to dispatch task {task.id} to worker {worker.name}: {e}")
        else:
            logger.warning(f"No online workers available for task {task.id}")
            
    return dispatched_count
