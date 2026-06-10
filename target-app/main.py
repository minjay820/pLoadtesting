"""
nebula-load-tester — Target Application
========================================
壓測靶機：提供四個模擬真實業務情境的 API Endpoint。

Endpoints
---------
GET  /api/health          ─ 健康檢查
GET  /api/cpu-bound       ─ CPU 密集型任務（費氏數列）
GET  /api/io-bound        ─ I/O 密集型任務（非同步等待）
POST /api/data            ─ 接收 JSON，回傳 100 筆模擬資料
"""

import asyncio
import random
import string
import time
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App 初始化
# ---------------------------------------------------------------------------

app = FastAPI(
    title="nebula-load-tester · Target App",
    description="壓測靶機：提供 CPU-bound、I/O-bound、資料回傳等模擬情境",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str


class CpuBoundResponse(BaseModel):
    n: int
    result: float   # 浮點數，避免大整數序列化問題
    elapsed_ms: float


class IoBoundResponse(BaseModel):
    delay: float
    message: str


class DataRequest(BaseModel):
    id: int = Field(..., description="請求識別碼，必須為正整數", gt=0)
    payload: str = Field(..., description="任意字串 payload", min_length=1, max_length=4096)


class DataItem(BaseModel):
    index: int
    ref_id: int
    name: str
    value: float
    tag: str


class DataResponse(BaseModel):
    request_id: int
    count: int
    items: list[DataItem]


# ---------------------------------------------------------------------------
# 工具函式
# ---------------------------------------------------------------------------


def _cpu_burn(n: int) -> tuple[float, float]:
    """
    執行 CPU 密集型計算，回傳 (結果, 耗時毫秒)。

    策略：重複執行浮點乘累加迴圈 n 次。
    - 每次迭代執行一次 float mul 與一次 float add，
      確保 CPU 維持運算狀態，不被編譯器優化消除。
    - 結果始終為小數，避免 Python 3.11+ 的 int→str
      序列化位數限制（4300 digits）。
    - n=1_000_000 在一般現代 CPU 上約耗費 ~100ms。
    """
    start = time.perf_counter()
    acc: float = 1.0
    for i in range(1, n + 1):
        acc = acc * 1.000_001 + i * 0.000_001
    elapsed_ms = (time.perf_counter() - start) * 1000
    return round(acc, 6), elapsed_ms


def _random_str(length: int = 8) -> str:
    """產生指定長度的隨機英數字串，用於填充模擬資料。"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _generate_items(ref_id: int, count: int = 100) -> list[DataItem]:
    """
    產生 count 筆模擬資料，模擬資料庫查詢回傳大量結果的情境。
    每筆資料約 80–120 bytes，100 筆約 8–12 KB，
    足以對網路頻寬與記憶體序列化造成可量測的壓力。
    """
    return [
        DataItem(
            index=i,
            ref_id=ref_id,
            name=f"item-{_random_str(6)}",
            value=round(random.uniform(0.0, 9999.99), 4),
            tag=_random_str(4),
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="健康檢查",
    tags=["Utility"],
)
async def health() -> HealthResponse:
    """
    回傳 HTTP 200 與 `{"status": "ok"}`。
    壓測工具用此 endpoint 確認服務存活，通常設為 pre-flight 檢查。
    """
    return HealthResponse(status="ok")


@app.get(
    "/api/cpu-bound",
    response_model=CpuBoundResponse,
    summary="CPU 密集型任務",
    tags=["Load Scenarios"],
)
async def cpu_bound(
    n: int = Query(
        default=1_000_000,
        ge=1,
        le=50_000_000,
        description="迴圈迭代次數（預設 1_000_000，約產生 ~100ms CPU 時間）",
    ),
) -> CpuBoundResponse:
    """
    執行 **n** 次浮點乘累加迴圈，模擬 CPU 密集型工作負載。

    - 預設 `n=1_000_000` 在一般現代 CPU 上約耗費 **~100ms**。
    - 使用 `asyncio.to_thread` 將阻塞計算移至 Thread Pool，
      確保 Event Loop 不被卡住，其他請求仍可並行處理。
    - 調高 `n` 可線性增加 CPU 壓力（例如 `n=5_000_000` ≈ 500ms）。
    """
    # 將同步阻塞計算卸載到 Thread Pool，保持 Event Loop 暢通
    result, elapsed_ms = await asyncio.to_thread(_cpu_burn, n)
    return CpuBoundResponse(n=n, result=result, elapsed_ms=round(elapsed_ms, 3))


@app.get(
    "/api/io-bound",
    response_model=IoBoundResponse,
    summary="I/O 密集型任務",
    tags=["Load Scenarios"],
)
async def io_bound(
    delay: float = Query(
        default=2.0,
        ge=0.0,
        le=30.0,
        description="模擬 I/O 等待的秒數（預設 2.0 秒）",
    ),
) -> IoBoundResponse:
    """
    使用 `asyncio.sleep` 模擬外部 I/O 延遲（資料庫查詢、第三方 API 呼叫等）。

    - 非同步等待不佔用 Thread，可支援極高的並發連線數。
    - `delay` 參數讓壓測工具可動態控制延遲，模擬不同的 SLA 情境。
    """
    await asyncio.sleep(delay)
    return IoBoundResponse(
        delay=delay,
        message=f"模擬 I/O 等待完成，耗時 {delay:.2f} 秒",
    )


@app.post(
    "/api/data",
    response_model=DataResponse,
    summary="接收 JSON，回傳 100 筆模擬資料",
    tags=["Load Scenarios"],
)
async def data(body: DataRequest) -> DataResponse:
    """
    接收 `{"id": int, "payload": str}` 的 JSON Body，
    驗證後回傳包含 **100 筆**模擬資料的 JSON Array。

    - 測試目標：JSON 序列化效能、記憶體分配、網路頻寬。
    - 每筆資料約 80–120 bytes，100 筆合計約 **8–12 KB** 回應。
    - `payload` 欄位在此 Phase 僅做格式驗證，不寫入任何持久化儲存。
    """
    # 將資料生成移至 Thread Pool（純 CPU 工作，避免阻塞 Event Loop）
    items: list[DataItem] = await asyncio.to_thread(_generate_items, body.id, 100)
    return DataResponse(request_id=body.id, count=len(items), items=items)


# ---------------------------------------------------------------------------
# 本地開發入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
