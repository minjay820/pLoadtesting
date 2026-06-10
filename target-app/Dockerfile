# =============================================================================
# pLoadtesting · Target App — Dockerfile
# =============================================================================
# 使用多階段建構 (Multi-stage Build)：
#   Stage 1 (builder)  ─ 安裝依賴，隔離建構環境
#   Stage 2 (runtime)  ─ 僅複製必要產出，最小化映像體積
# =============================================================================

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# 設定工作目錄
WORKDIR /build

# 先複製 requirements（利用 Docker layer cache：
# 只有 requirements.txt 變更時才重新安裝套件）
COPY requirements.txt .

# 安裝依賴到獨立目錄，方便後續 Stage 複製
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --target=/build/packages -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# 安全：以非 root 使用者執行
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# 複製已安裝的套件與應用程式碼
COPY --from=builder /build/packages /usr/local/lib/python3.11/site-packages
COPY main.py .

# 切換至非 root 使用者
USER appuser

# 對外暴露 Port
EXPOSE 8000

# 健康檢查：每 30 秒確認服務存活
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 啟動指令：
# --workers 1         ─ 單 Worker，方便壓測工具精確量測單節點效能
# --loop uvloop       ─ 啟用高效能 Event Loop（uvicorn[standard] 已包含）
# --access-log        ─ 記錄所有請求（壓測期間用於除錯）
CMD ["python", "-m", "uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--loop", "uvloop", \
     "--access-log"]
