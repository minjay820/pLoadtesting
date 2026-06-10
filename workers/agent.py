import os
import time
import socket
import logging
import requests
import psutil
import asyncio
import subprocess
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
import uvicorn

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

worker_state = {
    "worker_id": None,
    "active_task_count": 0
}

def get_local_ip():
    """嘗試取得本機向外連線的 IP，若失敗則回傳 127.0.0.1"""
    try:
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
        "capabilities": ["k6"]
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

def send_heartbeat():
    """取得系統資源並發送心跳"""
    worker_id = worker_state["worker_id"]
    if not worker_id:
        return
        
    url = f"{CONTROL_PLANE_URL}/api/workers/{worker_id}/heartbeat/"
    
    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    payload = {
        "status": "online",
        "active_task_count": worker_state["active_task_count"],
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

async def heartbeat_loop():
    """背景無窮迴圈，定時發送心跳"""
    while True:
        try:
            send_heartbeat()
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
        await asyncio.sleep(10)

def calculate_k6_summary(json_file_path: str):
    """從 k6 的 JSON 輸出中計算出 Control Plane 需要的摘要指標"""
    http_req_duration_values = []
    total_reqs = 0
    
    try:
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("type") == "Point" and data.get("metric") == "http_req_duration":
                            http_req_duration_values.append(data["data"]["value"])
                        if data.get("type") == "Point" and data.get("metric") == "http_reqs":
                            total_reqs += int(data["data"]["value"])
                    except json.JSONDecodeError:
                        continue
                        
        avg_response_ms = 0.0
        p95_response_ms = 0.0
        if http_req_duration_values:
            avg_response_ms = sum(http_req_duration_values) / len(http_req_duration_values)
            http_req_duration_values.sort()
            p95_index = int(len(http_req_duration_values) * 0.95)
            # handle index out of bounds if len is small
            p95_index = min(p95_index, len(http_req_duration_values) - 1)
            p95_response_ms = http_req_duration_values[p95_index]
            
        return {
            "avg_response_ms": avg_response_ms,
            "p95_response_ms": p95_response_ms,
            "throughput_rps": total_reqs / 60.0, # 假設 60 秒的壓測
            "raw_report": {"message": "k6 execution finished successfully", "total_requests": total_reqs}
        }
    except Exception as e:
        logger.error(f"Error parsing k6 results: {e}")
        return {
            "avg_response_ms": 0.0,
            "p95_response_ms": 0.0,
            "throughput_rps": 0.0,
            "raw_report": {"error": str(e)}
        }

def execute_task(task_id: str, engine: str, script_path: str, parameters: dict):
    worker_state["active_task_count"] += 1
    logger.info(f"Starting execution for task {task_id} with script {script_path}")
    
    output_file = f"/tmp/result_{task_id}.json"
    if os.path.isabs(script_path):
        full_script_path = script_path
    else:
        full_script_path = os.path.join("/app", script_path)
    
    try:
        if engine == "k6":
            cmd = ["k6", "run", "--out", f"json={output_file}", full_script_path]
            
            env = os.environ.copy()
            if parameters:
                for k, v in parameters.items():
                    env[k] = str(v)
            
            logger.info(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(cmd, env=env, capture_output=True, text=True)
            logger.info(f"Task {task_id} exited with {process.returncode}")
            
            if process.returncode != 0:
                logger.error(f"k6 execution failed: {process.stderr}")
            
            summary = calculate_k6_summary(output_file)
            
            url = f"{CONTROL_PLANE_URL}/api/tasks/{task_id}/results/"
            try:
                resp = requests.post(url, json=summary, timeout=10)
                resp.raise_for_status()
                logger.info(f"Successfully posted results for task {task_id}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to post results for task {task_id}: {e}")
                
        else:
            logger.warning(f"Unsupported engine: {engine}")
            
    except Exception as e:
        logger.error(f"Exception while executing task {task_id}: {e}")
        
    finally:
        worker_state["active_task_count"] -= 1

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting pLoadtesting Worker Agent (FastAPI)...")
    psutil.cpu_percent(interval=None) # Initialize
    
    worker_state["worker_id"] = register_worker()
    
    # Start heartbeat loop
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    yield
    
    # Shutdown
    heartbeat_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.post("/execute")
async def execute_endpoint(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    task_id = data.get("task_id")
    engine = data.get("engine")
    script_path = data.get("script_path")
    parameters = data.get("parameters", {})
    
    if not task_id or not script_path:
        return JSONResponse(status_code=400, content={"detail": "Missing task_id or script_path"})
        
    background_tasks.add_task(execute_task, task_id, engine, script_path, parameters)
    
    return JSONResponse(status_code=202, content={"message": "Accepted", "task_id": task_id})

if __name__ == "__main__":
    uvicorn.run("agent:app", host="0.0.0.0", port=WORKER_PORT, reload=False)
