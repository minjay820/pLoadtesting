from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    """測試健康檢查 Endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cpu_bound():
    """測試 CPU 密集型 Endpoint"""
    # 測試預設值 n=1_000_000
    response = client.get("/api/cpu-bound")
    assert response.status_code == 200
    data = response.json()
    assert "n" in data
    assert "result" in data
    assert "elapsed_ms" in data
    assert data["n"] == 1000000

    # 測試帶入參數 n=100
    response = client.get("/api/cpu-bound?n=100")
    assert response.status_code == 200
    data = response.json()
    assert data["n"] == 100


def test_io_bound():
    """測試 I/O 密集型 Endpoint"""
    # 測試帶入較短的 delay 避免測試跑太久
    response = client.get("/api/io-bound?delay=0.1")
    assert response.status_code == 200
    data = response.json()
    assert data["delay"] == 0.1
    assert "message" in data


def test_data():
    """測試資料回傳 Endpoint"""
    payload = {"id": 1, "payload": "hello-world"}
    response = client.post("/api/data", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == 1
    assert data["count"] == 100
    assert len(data["items"]) == 100
    # 驗證每個 DataItem 欄位
    first_item = data["items"][0]
    assert "index" in first_item
    assert "ref_id" in first_item
    assert "name" in first_item
    assert "value" in first_item
    assert "tag" in first_item
    assert first_item["ref_id"] == 1


def test_data_invalid():
    """測試資料回傳 validation 錯誤"""
    # 測試 id 必須大於 0
    payload = {"id": 0, "payload": "hello-world"}
    response = client.post("/api/data", json=payload)
    assert response.status_code == 422

    # 測試 payload 長度不可小於 1
    payload = {"id": 1, "payload": ""}
    response = client.post("/api/data", json=payload)
    assert response.status_code == 422
