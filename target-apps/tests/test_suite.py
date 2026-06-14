from importlib import import_module
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
TARGET_APPS_DIR = ROOT_DIR / "target-apps"
MANIFESTS_DIR = TARGET_APPS_DIR / "manifests"

MANIFEST_FILES = sorted(MANIFESTS_DIR.glob("*.yaml"))
APP_MODULES = {
    "echo-api": "echo_api",
    "latency-api": "latency_api",
    "error-api": "error_api",
    "resource-api": "resource_api",
    "payload-api": "payload_api",
    "crud-api": "crud_api",
    "auth-flow-api": "auth_flow_api",
}


def load_manifest(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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

    resource_client = TestClient(import_module("resource_api").app)
    assert resource_client.get("/api/cpu?iterations=3000000").status_code == 422
    assert resource_client.get("/api/memory?mb=128").status_code == 422
    assert resource_client.get("/api/io?kb=2048").status_code == 422


def test_crud_and_auth_flow_workloads():
    crud_client = TestClient(import_module("crud_api").app)
    created = crud_client.post("/api/items", json={"name": "demo", "value": 3})
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert crud_client.get(f"/api/items/{item_id}").status_code == 200

    auth_client = TestClient(import_module("auth_flow_api").app)
    login = auth_client.post("/api/login", json={"username": "alice", "password": "demo-password"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert auth_client.get("/api/profile", headers=headers).status_code == 200
    checkout = auth_client.post("/api/checkout", json={"sku": "sku-1", "quantity": 2}, headers=headers)
    assert checkout.status_code == 200


def test_compose_and_readme_commands_are_consistent():
    compose = yaml.safe_load((TARGET_APPS_DIR / "docker-compose.target-apps.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    readme = (TARGET_APPS_DIR / "README.md").read_text(encoding="utf-8")

    for target_app_id, manifest in ((load_manifest(path)["target_app_id"], load_manifest(path)) for path in MANIFEST_FILES):
        assert target_app_id in services
        assert manifest["base_url"] in readme

    assert "docker compose -f target-apps/docker-compose.target-apps.yml up --build -d" in readme
    assert "docker compose -f target-apps/docker-compose.target-apps.yml down" in readme
