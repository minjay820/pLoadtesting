from importlib import import_module
from pathlib import Path
import tarfile
import io

import yaml
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
TARGET_APPS_DIR = ROOT_DIR / "target-apps"
MANIFESTS_DIR = TARGET_APPS_DIR / "manifests"
TEMPLATES_DIR = TARGET_APPS_DIR / "task-templates"

EXACT_PROFILE_MATRIX = {
    "echo-k6-smoke": "echo-jmeter-smoke",
    "latency-k6-delay": "latency-jmeter-delay",
    "error-k6-flaky": "error-jmeter-flaky",
    "resource-k6-cpu": "resource-jmeter-cpu",
    "crud-k6-flow": "crud-jmeter-flow",
    "auth-k6-checkout": "auth-jmeter-checkout",
    "auth-k6-refresh-flow": "auth-jmeter-refresh-flow",
    "auth-k6-failure-branches": "auth-jmeter-failure-branches",
    "auth-k6-session-flow": "auth-jmeter-session-flow",
    "auth-k6-mfa-flow": "auth-jmeter-mfa-flow",
    "sse-k6-smoke": "sse-jmeter-smoke",
    "sse-k6-ticker": "sse-jmeter-ticker",
    "sse-k6-progress-heavy": "sse-jmeter-progress-heavy",
    "ws-k6-echo-smoke": "ws-jmeter-echo-smoke",
    "ws-k6-broadcast-smoke": "ws-jmeter-broadcast-smoke",
    "db-k6-crud-smoke": "db-jmeter-crud-smoke",
    "db-k6-list-filter": "db-jmeter-list-filter",
    "payload-k6-file-download": "payload-jmeter-file-download",
    "payload-k6-file-roundtrip": "payload-jmeter-file-roundtrip",
    "payload-k6-archive-read-many": "payload-jmeter-archive-read-many",
    "payload-k6-tar-selective-fetch": "payload-jmeter-tar-selective-fetch",
}

MANIFEST_FILES = sorted(MANIFESTS_DIR.glob("*.yaml"))
TEMPLATE_FILES = sorted(TEMPLATES_DIR.glob("*.yaml"))
APP_MODULES = {
    "echo-api": "echo_api",
    "latency-api": "latency_api",
    "error-api": "error_api",
    "resource-api": "resource_api",
    "payload-api": "payload_api",
    "crud-api": "crud_api",
    "auth-flow-api": "auth_flow_api",
    "sse-api": "sse_api",
    "ws-api": "ws_api",
    "db-api": "db_api",
}


def load_manifest(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def demo_mfa_code(username: str, channel: str) -> str:
    total = sum(f"{username}|{channel}".encode("utf-8"))
    return f"{(total * 137) % 1_000_000:06d}"


def test_manifest_metadata_schema_is_loadable():
    assert len(MANIFEST_FILES) == len(APP_MODULES)
    for manifest_path in MANIFEST_FILES:
        manifest = load_manifest(manifest_path)
        for field in (
            "target_app_id",
            "display_name",
            "runtime",
            "protocol",
            "base_url",
            "workload_types",
            "endpoints",
            "safe_limits",
            "default_profile",
            "notes",
        ):
            assert field in manifest
        assert manifest["target_app_id"] in APP_MODULES


def test_task_templates_are_loadable_and_point_to_real_assets():
    assert len(TEMPLATE_FILES) == len(APP_MODULES)
    for template_path in TEMPLATE_FILES:
        template_doc = load_manifest(template_path)
        assert template_doc["target_app_id"] in APP_MODULES
        assert template_doc["profiles"]
        for profile in template_doc["profiles"]:
            assert profile["engine"] in {"k6", "jmeter"}
            script_path = ROOT_DIR / profile["script_path"]
            assert script_path.exists(), f"Missing sample script or plan: {script_path}"
            assert profile["target_url"].startswith("http://127.0.0.1:")
    assert (TARGET_APPS_DIR / "scripts" / "smoke_docker_target_apps.sh").exists()


def test_every_target_catalog_has_k6_and_jmeter_coverage():
    coverage: dict[str, set[str]] = {}
    for template_path in TEMPLATE_FILES:
        template_doc = load_manifest(template_path)
        coverage[template_doc["target_app_id"]] = {profile["engine"] for profile in template_doc["profiles"]}

    for target_app_id in APP_MODULES:
        assert coverage[target_app_id] == {"k6", "jmeter"}


def test_exact_profile_matrix_has_both_k6_and_jmeter_profiles():
    all_profiles = {}
    for template_path in TEMPLATE_FILES:
        template_doc = load_manifest(template_path)
        for profile in template_doc["profiles"]:
            all_profiles[profile["target_profile_id"]] = profile["engine"]

    for k6_profile, jmeter_profile in EXACT_PROFILE_MATRIX.items():
        assert all_profiles[k6_profile] == "k6"
        assert all_profiles[jmeter_profile] == "jmeter"


def test_every_target_health_endpoint_is_stable():
    for target_app_id, module_name in APP_MODULES.items():
        app = import_module(module_name).app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["target_app_id"] == target_app_id


def test_delay_error_payload_and_resource_limits():
    latency_client = TestClient(import_module("latency_api").app)
    assert latency_client.get("/api/delay/6000").status_code == 422

    error_client = TestClient(import_module("error_api").app)
    assert error_client.get("/api/status/700").status_code == 422
    flaky_fail = error_client.get("/api/flaky?rate=1&deterministic=true&request_key=ci")
    assert flaky_fail.status_code == 503

    payload_client = TestClient(import_module("payload_api").app)
    assert payload_client.get("/api/download?kb=600").status_code == 422
    oversized_body = "x" * (262_144 + 1)
    assert payload_client.post("/api/upload", content=oversized_body).status_code == 422
    assert payload_client.get("/api/files/manifest?count=21").status_code == 422
    assert payload_client.get("/api/files/fixture-1?kb=257").status_code == 422
    assert payload_client.get("/api/files/archive?count=11").status_code == 422
    assert payload_client.get("/api/files/read-many?kb_per_file=65").status_code == 422
    assert payload_client.get("/api/files/tar-package?file_ids=fixture-1&file_ids=fixture-2&file_ids=fixture-3&file_ids=fixture-4&file_ids=fixture-5&file_ids=fixture-6&file_ids=fixture-7&file_ids=fixture-8&file_ids=fixture-9").status_code == 422
    assert payload_client.post("/api/files/upload?filename=demo.bin", content=b"x" * (262_144 + 1)).status_code == 422
    assert payload_client.post(
        "/api/files/selective-fetch",
        json={"file_ids": [f"fixture-{index}" for index in range(1, 10)], "kb_per_file": 8},
    ).status_code == 422

    resource_client = TestClient(import_module("resource_api").app)
    assert resource_client.get("/api/cpu?iterations=3000000").status_code == 422
    assert resource_client.get("/api/memory?mb=128").status_code == 422
    assert resource_client.get("/api/io?kb=2048").status_code == 422

    sse_client = TestClient(import_module("sse_api").app)
    assert sse_client.get("/api/events?count=101").status_code == 422
    assert sse_client.get("/api/events?interval_ms=5001").status_code == 422
    assert sse_client.get("/api/progress-heavy?steps=61").status_code == 422


def test_crud_and_auth_flow_workloads():
    crud_client = TestClient(import_module("crud_api").app)
    created = crud_client.post("/api/items", json={"name": "demo", "value": 3})
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert crud_client.get(f"/api/items/{item_id}").status_code == 200

    auth_client = TestClient(import_module("auth_flow_api").app)
    login = auth_client.post(
        "/api/login",
        json={"username": "alice", "password": "demo-password", "access_token_uses": 2, "refresh_uses": 2},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    refresh_token = login.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert auth_client.get("/api/profile", headers=headers).status_code == 200
    checkout = auth_client.post("/api/checkout", json={"sku": "sku-1", "quantity": 2}, headers=headers)
    assert checkout.status_code == 200
    expired = auth_client.get("/api/profile", headers=headers)
    assert expired.status_code == 401
    refreshed = auth_client.post("/api/refresh", json={"refresh_token": refresh_token, "access_token_uses": 2})
    assert refreshed.status_code == 200
    refreshed_token = refreshed.json()["access_token"]
    refreshed_headers = {"Authorization": f"Bearer {refreshed_token}"}
    assert auth_client.get("/api/profile", headers=refreshed_headers).status_code == 200
    assert auth_client.post("/api/logout", headers=refreshed_headers).status_code == 200
    assert auth_client.get("/api/profile", headers=refreshed_headers).status_code == 401
    assert auth_client.post("/api/login", json={"username": "alice", "password": "bad-password"}).status_code == 401
    session_login = auth_client.post(
        "/api/session/login",
        json={"username": "alice", "password": "demo-password", "session_uses": 2},
    )
    assert session_login.status_code == 200
    assert auth_client.get("/api/session/profile").status_code == 200
    assert auth_client.post("/api/session/logout").status_code == 200
    assert auth_client.get("/api/session/profile").status_code == 401
    mfa_start = auth_client.post(
        "/api/mfa/login/start",
        json={"username": "alice", "password": "demo-password", "channel": "sms"},
    )
    assert mfa_start.status_code == 200
    challenge_id = mfa_start.json()["challenge_id"]
    mfa_verify = auth_client.post(
        "/api/mfa/login/verify",
        json={
            "challenge_id": challenge_id,
            "code": demo_mfa_code("alice", "sms"),
            "issue_mode": "bearer",
            "access_token_uses": 2,
            "refresh_uses": 1,
        },
    )
    assert mfa_verify.status_code == 200
    mfa_access_token = mfa_verify.json()["access_token"]
    assert auth_client.get("/api/profile", headers={"Authorization": f"Bearer {mfa_access_token}"}).status_code == 200
    reused_challenge = auth_client.post(
        "/api/mfa/login/verify",
        json={"challenge_id": challenge_id, "code": demo_mfa_code("alice", "sms"), "issue_mode": "bearer"},
    )
    assert reused_challenge.status_code == 401

    payload_client = TestClient(import_module("payload_api").app)
    manifest = payload_client.get("/api/files/manifest?count=2&kb_per_file=8")
    assert manifest.status_code == 200
    assert manifest.json()["count"] == 2
    file_download = payload_client.get("/api/files/fixture-1?kb=8")
    assert file_download.status_code == 200
    assert file_download.headers["content-type"] == "application/octet-stream"
    assert "attachment;" in file_download.headers["content-disposition"]
    file_upload = payload_client.post(
        "/api/files/upload?filename=fixture-1.bin",
        content=file_download.content,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert file_upload.status_code == 200
    assert file_upload.json()["received_bytes"] == 8 * 1024
    fixture_pack = payload_client.get("/api/files/fixture-pack?count=3&kb_per_file=10")
    assert fixture_pack.status_code == 200
    assert fixture_pack.json()["count"] == 3
    archive = payload_client.get("/api/files/archive?count=3&kb_per_file=10")
    assert archive.status_code == 200
    assert archive.headers["content-type"] == "application/zip"
    assert archive.content.startswith(b"PK")
    read_many = payload_client.get("/api/files/read-many?count=3&kb_per_file=10")
    assert read_many.status_code == 200
    assert read_many.json()["count"] == 3
    assert len(read_many.json()["combined_sha256_prefix"]) == 16
    selective_fetch = payload_client.post(
        "/api/files/selective-fetch",
        json={"file_ids": ["fixture-1", "fixture-3"], "kb_per_file": 10},
    )
    assert selective_fetch.status_code == 200
    assert selective_fetch.json()["selected_count"] == 2
    assert selective_fetch.json()["files"][0]["download_path"].startswith("/api/files/fixture-1")
    tar_package = payload_client.get("/api/files/tar-package?file_ids=fixture-1&file_ids=fixture-3&kb_per_file=10")
    assert tar_package.status_code == 200
    assert tar_package.headers["content-type"] == "application/x-tar"
    with tarfile.open(fileobj=io.BytesIO(tar_package.content), mode="r:") as archive:
        names = sorted(member.name for member in archive.getmembers())
        assert names == ["fixture-1.bin", "fixture-3.bin"]

    sse_client = TestClient(import_module("sse_api").app)
    response = sse_client.get("/api/ticker?count=3&interval_ms=0&deterministic=true")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: ticker" in response.text
    assert '"sequence":1' in response.text
    progress_heavy = sse_client.get("/api/progress-heavy?steps=4&interval_ms=0&deterministic=true")
    assert progress_heavy.status_code == 200
    assert "event: progress-heavy" in progress_heavy.text
    assert '"phase":"queued"' in progress_heavy.text


def test_websocket_and_db_heavy_workloads():
    ws_client = TestClient(import_module("ws_api").app)
    with ws_client.websocket_connect("/ws/echo?deterministic=true") as websocket:
        welcome = websocket.receive_json()
        assert welcome["event"] == "welcome"
        websocket.send_text("hello")
        echoed = websocket.receive_json()
        assert echoed["event"] == "echo"
        assert echoed["message"] == "hello"

    with ws_client.websocket_connect("/ws/echo?deterministic=true") as websocket:
        websocket.receive_json()
        websocket.send_text("x" * 1025)
        closed = websocket.receive()
        assert closed["type"] == "websocket.close"
        assert closed["code"] == 1009

    with ws_client.websocket_connect("/ws/broadcast/room-a?client_id=subscriber&deterministic=true") as subscriber:
        subscriber.receive_json()
        with ws_client.websocket_connect("/ws/broadcast/room-a?client_id=publisher&deterministic=true") as publisher:
            publisher.receive_json()
            publisher.send_text("fanout")
            broadcast = subscriber.receive_json()
            assert broadcast["event"] == "broadcast"
            assert broadcast["message"] == "fanout"

    db_client = TestClient(import_module("db_api").app)
    created = db_client.post(
        "/api/records",
        json={"name": "zeta", "category": "ops", "value": 91, "status": "ready"},
    )
    assert created.status_code == 201
    record_id = created.json()["id"]
    fetched = db_client.get(f"/api/records/{record_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "zeta"
    updated = db_client.patch(f"/api/records/{record_id}", json={"status": "archived"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "archived"
    listed = db_client.get("/api/records?category=ops&limit=5&sort_by=id&sort_order=asc")
    assert listed.status_code == 200
    assert listed.json()["count"] <= 5
    assert db_client.get("/api/records?limit=51").status_code == 422


def test_compose_and_readme_commands_are_consistent():
    compose = yaml.safe_load((TARGET_APPS_DIR / "docker-compose.target-apps.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    readme = (TARGET_APPS_DIR / "README.md").read_text(encoding="utf-8")

    for target_app_id, manifest in ((load_manifest(path)["target_app_id"], load_manifest(path)) for path in MANIFEST_FILES):
        assert target_app_id in services
        assert manifest["base_url"] in readme

    assert "docker compose -f target-apps/docker-compose.target-apps.yml up --build -d" in readme
    assert "docker compose -f target-apps/docker-compose.target-apps.yml down" in readme
