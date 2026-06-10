import os
import time
import socket
import logging
import requests
import psutil

# ── 設定日誌 ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ── 讀取環境變數 ─────────────────────────────────────────────────────────
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://localhost:9000")
WORKER_NAME       = os.getenv("WORKER_NAME", "worker-local-01")
WORKER_PORT       = 8100  # 預設，後續可以依據真實起 API server 改動

def get_local_ip():
    """嘗試取得本機向外連線的 IP，若失敗則回傳 127.0.0.1"""
    try:
        # 建立一個 UDP socket，不需要真實連線
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def register_worker() -> str:
    """向 Control Plane 註冊，回傳 Worker UUID"""
    url = f"{CONTROL_PLANE_URL}/api/workers/"
    ip_addr = get_local_ip()
    
    payload = {
        "name": WORKER_NAME,
        "ip_address": ip_addr,
        "port": WORKER_PORT,
        "capabilities": ["k6", "jmeter"]
    }
    
    while True:
        try:
            logger.info(f"Registering worker '{WORKER_NAME}' to {url} ...")
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            worker_id = data.get("id")
            logger.info(f"Registration successful! Worker ID: {worker_id}")
            return worker_id
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Registration failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def send_heartbeat(worker_id: str):
    """取得系統資源並發送心跳"""
    url = f"{CONTROL_PLANE_URL}/api/workers/{worker_id}/heartbeat/"
    
    # 取得系統資源快照
    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    payload = {
        "status": "online",
        "active_task_count": 0,  # MVP 階段暫不實作真實任務追蹤
        "resource_snapshot": {
            "cpu_pct": cpu_pct,
            "mem_pct": mem.percent,
            "disk_pct": disk.percent
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        logger.info(f"Heartbeat sent successfully. CPU: {cpu_pct}%, Mem: {mem.percent}%")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send heartbeat: {e}")

def main():
    logger.info("Starting Nebula Worker Agent...")
    # 初始化 CPU 測量
    psutil.cpu_percent(interval=None)
    
    # 註冊取得 UUID
    worker_id = register_worker()
    
    # 心跳迴圈
    while True:
        send_heartbeat(worker_id)
        time.sleep(10)

if __name__ == "__main__":
    main()
