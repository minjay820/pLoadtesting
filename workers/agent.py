import os
import time
import socket
import logging
import requests
import psutil
import asyncio
import subprocess
import json
import csv
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
import uvicorn

# ── InfluxDB v2 Client（可選，僅在環境變數存在時啟用）───────────────────────
try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
    _INFLUXDB_AVAILABLE = True
except ImportError:
    _INFLUXDB_AVAILABLE = False

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
API_TOKEN         = os.getenv("PLOADTESTING_API_TOKEN", "dev-api-token-change-me")

# ── InfluxDB v2 Observability 環境變數 ───────────────────────────────────
INFLUXDB_URL    = os.getenv("INFLUXDB_URL", "")      # e.g. http://influxdb:8086
INFLUXDB_TOKEN  = os.getenv("INFLUXDB_TOKEN", "")    # Admin token
INFLUXDB_ORG    = os.getenv("INFLUXDB_ORG", "ploadtesting")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "load_tests")

# InfluxDB v1 compatibility URL for k6 --out influxdb (line protocol)
# k6 v0.51 uses v1 line protocol; InfluxDB v2 provides /write compatibility endpoint
INFLUXDB_V1_URL = f"{INFLUXDB_URL}/api/v1/write" if INFLUXDB_URL else ""

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

def api_headers() -> dict:
    """Headers required by the Control Plane preview API."""
    return {"X-PLOADTESTING-API-TOKEN": API_TOKEN}


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
            resp = requests.post(url, json=payload, headers=api_headers(), timeout=10)
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
        "status": "busy" if worker_state["active_task_count"] > 0 else "online",
        "active_task_count": worker_state["active_task_count"],
        "resource_snapshot": {
            "cpu_pct": cpu_pct,
            "mem_pct": mem.percent,
            "disk_pct": disk.percent
        }
    }
    
    try:
        resp = requests.post(url, json=payload, headers=api_headers(), timeout=5)
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

def calculate_jmeter_summary(jtl_file_path: str):
    """從 JMeter 的 JTL (CSV) 輸出中計算出 Control Plane 需要的摘要指標"""
    response_times = []
    total_reqs = 0
    failed_reqs = 0
    
    start_time = None
    end_time = None

    try:
        if os.path.exists(jtl_file_path):
            with open(jtl_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        ts = int(row['timeStamp'])
                        elapsed = int(row['elapsed'])
                        success = row['success'].lower() == 'true'

                        if start_time is None or ts < start_time:
                            start_time = ts
                        if end_time is None or ts > end_time:
                            end_time = ts

                        response_times.append(elapsed)
                        total_reqs += 1
                        if not success:
                            failed_reqs += 1
                    except (KeyError, ValueError):
                        continue

        avg_response_ms = 0.0
        p95_response_ms = 0.0
        throughput_rps = 0.0

        if response_times:
            avg_response_ms = sum(response_times) / len(response_times)
            response_times.sort()
            p95_index = int(len(response_times) * 0.95)
            p95_index = min(p95_index, len(response_times) - 1)
            p95_response_ms = response_times[p95_index]

        if start_time and end_time and end_time > start_time:
            duration_s = (end_time - start_time) / 1000.0
            if duration_s > 0:
                throughput_rps = total_reqs / duration_s

        return {
            "avg_response_ms": avg_response_ms,
            "p95_response_ms": p95_response_ms,
            "throughput_rps": throughput_rps,
            "raw_report": {
                "message": "JMeter execution finished successfully",
                "total_requests": total_reqs,
                "failed_requests": failed_reqs
            }
        }
    except Exception as e:
        logger.error(f"Error parsing JMeter results: {e}")
        return {
            "avg_response_ms": 0.0,
            "p95_response_ms": 0.0,
            "throughput_rps": 0.0,
            "raw_report": {"error": str(e)}
        }

def post_task_result(task_id: str, payload: dict):
    """Post task execution results back to the Control Plane."""
    url = f"{CONTROL_PLANE_URL}/api/tasks/{task_id}/results/"
    resp = requests.post(url, json=payload, headers=api_headers(), timeout=10)
    resp.raise_for_status()


def push_summary_to_influxdb(task_id: str, engine: str, summary: dict, target_url: str = ""):
    """壓測完成後，將彙總指標寫入 InfluxDB v2。

    這是 k6/JMeter 即時串流之外的補充路徑，確保即使串流失敗，
    最終聚合結果（avg, p95, rps, status）仍會保存至 InfluxDB。

    Measurement: task_summary
    Tags:  task_id, engine, worker, status
    Fields: avg_response_ms, p95_response_ms, throughput_rps, error_rate
    """
    if not _INFLUXDB_AVAILABLE:
        logger.warning("influxdb-client not installed, skipping InfluxDB summary push")
        return
    if not INFLUXDB_URL or not INFLUXDB_TOKEN:
        logger.debug("InfluxDB not configured (INFLUXDB_URL/TOKEN missing), skipping summary push")
        return

    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)

        status = summary.get("execution_status", "unknown")
        avg_ms  = float(summary.get("avg_response_ms", 0.0))
        p95_ms  = float(summary.get("p95_response_ms", 0.0))
        rps     = float(summary.get("throughput_rps", 0.0))
        raw     = summary.get("raw_report", {})
        total   = int(raw.get("total_requests", 0))
        failed  = int(raw.get("failed_requests", 0))
        error_rate = (failed / total * 100.0) if total > 0 else 0.0

        point = (
            Point("task_summary")
            .tag("task_id", str(task_id))
            .tag("engine", engine)
            .tag("worker", WORKER_NAME)
            .tag("status", status)
            .tag("target_url", target_url or "")
            .field("avg_response_ms", avg_ms)
            .field("p95_response_ms", p95_ms)
            .field("throughput_rps", rps)
            .field("error_rate_pct", error_rate)
            .field("total_requests", total)
            .field("failed_requests", failed)
        )

        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
        client.close()
        logger.info(f"[InfluxDB] Summary pushed for task {task_id}: "
                    f"rps={rps:.1f}, p95={p95_ms:.1f}ms, status={status}")
    except Exception as e:
        # 非關鍵路徑：寫入失敗不影響主流程
        logger.error(f"[InfluxDB] Failed to push summary for task {task_id}: {e}")


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
            cmd = ["k6", "run", "--out", f"json={output_file}"]
            # Phase 6：若 InfluxDB 已設定，自動加入即時串流輸出
            # k6 v0.51+ 的 InfluxDB output 使用 v1 line protocol
            # InfluxDB v2 透過 /api/v1/write 相容端點接收
            if INFLUXDB_URL and INFLUXDB_TOKEN:
                influx_out = (
                    f"influxdb={INFLUXDB_URL}"
                    f"?org={INFLUXDB_ORG}"
                    f"&bucket={INFLUXDB_BUCKET}"
                    f"&token={INFLUXDB_TOKEN}"
                )
                cmd += ["--out", influx_out]
                logger.info(f"[InfluxDB] k6 real-time streaming enabled → {INFLUXDB_URL}")
            cmd += [full_script_path]
            
            env = os.environ.copy()
            if parameters:
                for k, v in parameters.items():
                    env[k] = str(v)
            
            logger.info(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(cmd, env=env, capture_output=True, text=True)
            logger.info(f"Task {task_id} exited with {process.returncode}")
            
            summary = calculate_k6_summary(output_file)
            summary["raw_report"].update({
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode,
            })
            if process.returncode != 0:
                logger.error(f"k6 execution failed: {process.stderr}")
                summary["execution_status"] = "failed"
                summary["error_message"] = process.stderr or f"k6 exited with code {process.returncode}"
            else:
                summary["execution_status"] = "completed"
            
            try:
                post_task_result(task_id, summary)
                logger.info(f"Successfully posted results for task {task_id}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to post results for task {task_id}: {e}")

            # Phase 6：壓測完成後推送彙總指標至 InfluxDB（補充路徑）
            push_summary_to_influxdb(
                task_id=task_id,
                engine="k6",
                summary=summary,
                target_url=parameters.get("target_url", "")
            )
                
        elif engine == "jmeter":
            output_jtl = f"/tmp/jmeter_{task_id}.jtl"
            output_log = f"/tmp/jmeter_{task_id}.log"
            cmd = ["jmeter", "-n", "-t", full_script_path, "-l", output_jtl, "-j", output_log]
            
            target_url = parameters.get("target_url")
            if target_url:
                parsed = urlparse(target_url)
                host = parsed.hostname
                port = parsed.port if parsed.port else (443 if parsed.scheme == "https" else 80)
                cmd.extend(["-JTARGET_HOST=" + str(host), "-JTARGET_PORT=" + str(port)])
                
            env = os.environ.copy()
            if parameters:
                for k, v in parameters.items():
                    if k != "target_url":
                        env[k] = str(v)
            
            logger.info(f"Running command: {' '.join(cmd)}")
            process = subprocess.run(cmd, env=env, capture_output=True, text=True)
            logger.info(f"Task {task_id} exited with {process.returncode}")
            
            summary = calculate_jmeter_summary(output_jtl)
            summary["raw_report"].update({
                "stdout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode,
            })
            if process.returncode != 0:
                logger.error(f"JMeter execution failed: {process.stderr}")
                summary["execution_status"] = "failed"
                summary["error_message"] = process.stderr or f"JMeter exited with code {process.returncode}"
            else:
                summary["execution_status"] = "completed"
            
            try:
                post_task_result(task_id, summary)
                logger.info(f"Successfully posted results for task {task_id}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to post results for task {task_id}: {e}")

            # Phase 6：壓測完成後推送彙總指標至 InfluxDB（補充路徑）
            push_summary_to_influxdb(
                task_id=task_id,
                engine="jmeter",
                summary=summary,
                target_url=parameters.get("target_url", "")
            )

        else:
            logger.warning(f"Unsupported engine: {engine}")
            try:
                post_task_result(task_id, {
                    "execution_status": "failed",
                    "error_message": f"Unsupported engine: {engine}",
                    "raw_report": {"error": f"Unsupported engine: {engine}"},
                })
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to post unsupported-engine result for task {task_id}: {e}")
            
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
    if request.headers.get("X-PLOADTESTING-API-TOKEN") != API_TOKEN:
        auth_header = request.headers.get("Authorization", "")
        bearer_token = ""
        if auth_header.lower().startswith("bearer "):
            bearer_token = auth_header.split(" ", 1)[1].strip()
        if bearer_token != API_TOKEN:
            return JSONResponse(status_code=403, content={"detail": "A valid API token is required."})

    data = await request.json()
    task_id = data.get("task_id")
    engine = data.get("engine")
    script_path = data.get("script_path")
    parameters = data.get("parameters", {})
    
    if not task_id or not engine or not script_path:
        return JSONResponse(status_code=400, content={"detail": "Missing task_id, engine, or script_path"})
        
    background_tasks.add_task(execute_task, task_id, engine, script_path, parameters)
    
    return JSONResponse(status_code=202, content={"message": "Accepted", "task_id": task_id})

if __name__ == "__main__":
    uvicorn.run("agent:app", host="0.0.0.0", port=WORKER_PORT, reload=False)
