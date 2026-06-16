import importlib.util
import hashlib
import subprocess
import sys
import types
from pathlib import Path
from unittest import mock


class _RequestsException(Exception):
    pass


class _FastAPI:
    def __init__(self, *args, **kwargs):
        pass

    def post(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


class _BackgroundTasks:
    def add_task(self, *args, **kwargs):
        pass


class _JSONResponse:
    def __init__(self, status_code=200, content=None):
        self.status_code = status_code
        self.content = content


def install_worker_dependency_stubs():
    """Import helper tests without requiring the full worker service stack."""
    requests_stub = types.ModuleType("requests")
    requests_stub.exceptions = types.SimpleNamespace(RequestException=_RequestsException)
    requests_stub.post = mock.Mock()
    sys.modules.setdefault("requests", requests_stub)

    psutil_stub = types.ModuleType("psutil")
    psutil_stub.cpu_percent = lambda interval=None: 0.0
    psutil_stub.virtual_memory = lambda: types.SimpleNamespace(percent=0.0)
    psutil_stub.disk_usage = lambda path: types.SimpleNamespace(percent=0.0)
    sys.modules.setdefault("psutil", psutil_stub)

    fastapi_stub = types.ModuleType("fastapi")
    fastapi_stub.FastAPI = _FastAPI
    fastapi_stub.BackgroundTasks = _BackgroundTasks
    fastapi_stub.Request = object
    sys.modules.setdefault("fastapi", fastapi_stub)

    responses_stub = types.ModuleType("fastapi.responses")
    responses_stub.JSONResponse = _JSONResponse
    sys.modules.setdefault("fastapi.responses", responses_stub)

    uvicorn_stub = types.ModuleType("uvicorn")
    uvicorn_stub.run = mock.Mock()
    sys.modules.setdefault("uvicorn", uvicorn_stub)


install_worker_dependency_stubs()

AGENT_PATH = Path(__file__).resolve().parents[1] / "agent.py"
ARTIFACTS_PATH = Path(__file__).resolve().parents[1] / "artifacts.py"
SPEC = importlib.util.spec_from_file_location("worker_agent", AGENT_PATH)
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)
ARTIFACTS_SPEC = importlib.util.spec_from_file_location("worker_artifacts", ARTIFACTS_PATH)
worker_artifacts = importlib.util.module_from_spec(ARTIFACTS_SPEC)
ARTIFACTS_SPEC.loader.exec_module(worker_artifacts)


def completed_process(cmd):
    return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")


def sample_shard():
    return {
        "shard_id": "users-a",
        "agent_selector": {"labels": ["zone:a", "engine:k6"]},
        "dataset": {
            "source": "artifact://datasets/users.csv",
            "format": "csv",
            "offset": 0,
            "limit": 2000,
        },
    }


def test_build_k6_artifact_manifest_entries_from_evidence():
    entries = worker_artifacts.build_artifact_manifest_entries(
        "task-1",
        "k6",
        {
            "raw_report": {"stdout": "ok", "stderr": "warn"},
            "artifact_evidence": {"has_summary_json": True},
        },
    )

    by_id = {entry["artifact_id"]: entry for entry in entries}
    assert by_id["k6-summary-json"]["state"] == "available"
    assert by_id["k6-summary-json"]["object_ref"] == "artifact://tasks/task-1/k6-summary-json"
    assert by_id["k6-stdout"]["state"] == "available"
    assert by_id["k6-stderr"]["state"] == "available"
    assert by_id["k6-engine-output"]["state"] == "available"


def test_build_artifact_manifest_returns_versioned_envelope():
    payload = worker_artifacts.build_artifact_manifest(
        "task-versioned",
        "k6",
        {"raw_report": {"stdout": "ok"}},
    )

    assert payload["artifact_manifest_version"] == "1.0"
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["artifact_id"] == "k6-summary-json"


def test_build_jmeter_artifact_manifest_entries_from_evidence():
    entries = worker_artifacts.build_artifact_manifest_entries(
        "task-2",
        "jmeter",
        {
            "raw_report": {"stdout": "ok", "stderr": "warn"},
            "artifact_evidence": {"has_jtl": True, "has_html_report": True},
        },
    )

    by_id = {entry["artifact_id"]: entry for entry in entries}
    assert by_id["jmeter-jtl"]["state"] == "available"
    assert by_id["jmeter-html-report"]["state"] == "available"
    assert by_id["jmeter-engine-output"]["state"] == "available"
    assert by_id["jmeter-jtl"]["object_ref"] == "artifact://tasks/task-2/jmeter-jtl"


def test_build_unknown_engine_artifact_manifest_entry():
    entries = worker_artifacts.build_artifact_manifest_entries(
        "task-3",
        "custom",
        {"raw_report": {"error": "unsupported"}},
    )

    assert len(entries) == 1
    assert entries[0]["artifact_id"] == "engine-output"
    assert entries[0]["state"] == "available"


def test_build_artifact_manifest_without_evidence_does_not_fake_available():
    entries = worker_artifacts.build_artifact_manifest_entries("task-4", "k6", {"raw_report": {}})

    by_id = {entry["artifact_id"]: entry for entry in entries}
    assert by_id["k6-summary-json"]["state"] == "planned"
    assert by_id["k6-summary-json"]["object_ref"] is None
    assert by_id["k6-stdout"]["state"] == "planned"
    assert by_id["k6-engine-output"]["state"] == "planned"


def test_build_artifact_manifest_does_not_expose_local_paths():
    entries = worker_artifacts.build_artifact_manifest_entries(
        "task-5",
        "jmeter",
        {"raw_report": {"stdout": "ok"}, "artifact_evidence": {"has_jtl": True}},
    )

    for entry in entries:
        assert entry["object_ref"] is None or entry["object_ref"].startswith("artifact://tasks/task-5/")
        assert "/tmp/" not in str(entry)
        assert "file:///" not in str(entry)


def test_stdout_evidence_generates_size_and_checksum():
    entries = worker_artifacts.build_artifact_manifest_entries(
        "task-stdout",
        "k6",
        {"raw_report": {"stdout": "hello"}},
    )

    stdout_entry = {entry["artifact_id"]: entry for entry in entries}["k6-stdout"]
    assert stdout_entry["size_bytes"] == 5
    assert stdout_entry["checksum_sha256"] == hashlib.sha256(b"hello").hexdigest()


def test_stderr_evidence_generates_size_and_checksum():
    entries = worker_artifacts.build_artifact_manifest_entries(
        "task-stderr",
        "jmeter",
        {"raw_report": {"stderr": "warn"}},
    )

    stderr_entry = {entry["artifact_id"]: entry for entry in entries}["jmeter-stderr"]
    assert stderr_entry["size_bytes"] == 4
    assert stderr_entry["checksum_sha256"] == hashlib.sha256(b"warn").hexdigest()


def test_raw_report_evidence_generates_size_and_checksum():
    entries = worker_artifacts.build_artifact_manifest_entries(
        "task-raw",
        "custom",
        {"raw_report": {"error": "unsupported"}},
    )

    entry = entries[0]
    assert entry["size_bytes"] is not None
    assert len(entry["checksum_sha256"]) == 64


def test_checksum_is_64_char_hex():
    entries = worker_artifacts.build_artifact_manifest_entries(
        "task-hash",
        "k6",
        {"raw_report": {"stdout": "hash-me"}},
    )

    stdout_entry = {entry["artifact_id"]: entry for entry in entries}["k6-stdout"]
    assert len(stdout_entry["checksum_sha256"]) == 64
    assert stdout_entry["checksum_sha256"] == stdout_entry["checksum_sha256"].lower()


def test_k6_env_includes_execution_settings():
    execution = {
        "duration_seconds": 600,
        "ramp_up_seconds": 30,
        "ramp_down_seconds": 15,
        "stop_policy": "graceful_stop",
        "graceful_stop_seconds": 30,
        "max_run_seconds": 690,
        "iteration_limit": None,
        "data_policy": "duration_first",
    }

    with mock.patch.object(agent.subprocess, "run", return_value=completed_process(["k6"])) as run_mock, \
        mock.patch.object(agent, "calculate_k6_summary", return_value={"raw_report": {}}), \
        mock.patch.object(agent, "post_task_result"), \
        mock.patch.object(agent, "push_summary_to_influxdb"):
        agent.execute_task(
            "task-1",
            "k6",
            "engines/k6/target_apps_payload_download.js",
            {"TARGET_URL": "http://target", "execution": execution},
        )

    kwargs = run_mock.call_args.kwargs
    assert kwargs["timeout"] == 690
    assert kwargs["env"]["DURATION_SECONDS"] == "600"
    assert kwargs["env"]["RAMP_UP_SECONDS"] == "30"
    assert kwargs["env"]["RAMP_DOWN_SECONDS"] == "15"
    assert kwargs["env"]["GRACEFUL_STOP_SECONDS"] == "30"
    assert kwargs["env"]["STOP_POLICY"] == "graceful_stop"
    assert kwargs["env"]["DATA_POLICY"] == "duration_first"


def test_k6_env_includes_shard_metadata():
    shard = sample_shard()

    with mock.patch.object(agent.subprocess, "run", return_value=completed_process(["k6"])) as run_mock, \
        mock.patch.object(agent, "calculate_k6_summary", return_value={"raw_report": {}}), \
        mock.patch.object(agent, "post_task_result") as post_mock, \
        mock.patch.object(agent, "push_summary_to_influxdb"):
        agent.execute_task(
            "task-shard-k6",
            "k6",
            "engines/k6/target_apps_payload_download.js",
            {"TARGET_URL": "http://target", "shard": shard},
        )

    kwargs = run_mock.call_args.kwargs
    assert kwargs["env"]["SHARD_ID"] == "users-a"
    assert kwargs["env"]["DATASET_SOURCE"] == "artifact://datasets/users.csv"
    assert kwargs["env"]["DATASET_FORMAT"] == "csv"
    assert kwargs["env"]["DATASET_OFFSET"] == "0"
    assert kwargs["env"]["DATASET_LIMIT"] == "2000"
    assert "shard" not in kwargs["env"]
    payload = post_mock.call_args.args[1]
    assert payload["artifact_manifest"]["artifact_manifest_version"] == "1.0"
    assert payload["artifact_manifest"]["items"][0]["artifact_id"] == "k6-summary-json"
    assert all("/tmp/" not in str(entry) for entry in payload["artifact_manifest"]["items"])
    assert payload["raw_report"]["shard"] == shard


def test_jmeter_command_includes_execution_properties():
    execution = {
        "duration_seconds": 20,
        "ramp_up_seconds": 5,
        "ramp_down_seconds": 0,
        "stop_policy": "graceful_stop",
        "graceful_stop_seconds": 10,
        "max_run_seconds": 40,
        "iteration_limit": 2,
        "data_policy": "iteration_first",
    }

    with mock.patch.object(agent.subprocess, "run", return_value=completed_process(["jmeter"])) as run_mock, \
        mock.patch.object(agent, "calculate_jmeter_summary", return_value={"raw_report": {}}), \
        mock.patch.object(agent, "post_task_result"), \
        mock.patch.object(agent, "push_summary_to_influxdb"):
        agent.execute_task(
            "task-2",
            "jmeter",
            "engines/jmeter/target_apps_payload_crud_plan.jmx",
            {"target_url": "http://127.0.0.1:18084", "execution": execution},
        )

    cmd = run_mock.call_args.args[0]
    assert "-Jduration_seconds=20" in cmd
    assert "-Jramp_up_seconds=5" in cmd
    assert "-Jramp_down_seconds=0" in cmd
    assert "-Jstop_policy=graceful_stop" in cmd
    assert "-Jgraceful_stop_seconds=10" in cmd
    assert "-Jiteration_limit=2" in cmd
    assert run_mock.call_args.kwargs["timeout"] == 40


def test_jmeter_command_includes_shard_properties():
    shard = sample_shard()

    with mock.patch.object(agent.subprocess, "run", return_value=completed_process(["jmeter"])) as run_mock, \
        mock.patch.object(agent, "calculate_jmeter_summary", return_value={"raw_report": {}}), \
        mock.patch.object(agent, "post_task_result") as post_mock, \
        mock.patch.object(agent, "push_summary_to_influxdb"):
        agent.execute_task(
            "task-shard-jmeter",
            "jmeter",
            "engines/jmeter/target_apps_payload_crud_plan.jmx",
            {"target_url": "http://127.0.0.1:18084", "shard_metadata": shard},
        )

    cmd = run_mock.call_args.args[0]
    assert "-Jshard_id=users-a" in cmd
    assert "-Jdataset_source=artifact://datasets/users.csv" in cmd
    assert "-Jdataset_format=csv" in cmd
    assert "-Jdataset_offset=0" in cmd
    assert "-Jdataset_limit=2000" in cmd
    assert not any(item.startswith("-Jshard_metadata=") for item in cmd)
    payload = post_mock.call_args.args[1]
    assert payload["artifact_manifest"]["artifact_manifest_version"] == "1.0"
    assert payload["artifact_manifest"]["items"][0]["artifact_id"] == "jmeter-jtl"
    assert all("/tmp/" not in str(entry) for entry in payload["artifact_manifest"]["items"])
    assert payload["raw_report"]["shard"] == shard


def test_without_execution_preserves_unbounded_subprocess_call():
    with mock.patch.object(agent.subprocess, "run", return_value=completed_process(["k6"])) as run_mock, \
        mock.patch.object(agent, "calculate_k6_summary", return_value={"raw_report": {}}), \
        mock.patch.object(agent, "post_task_result"), \
        mock.patch.object(agent, "push_summary_to_influxdb"):
        agent.execute_task(
            "task-3",
            "k6",
            "engines/k6/target_apps_payload_download.js",
            {"TARGET_URL": "http://target"},
        )

    kwargs = run_mock.call_args.kwargs
    assert kwargs["timeout"] is None
    assert "DURATION_SECONDS" not in kwargs["env"]
    assert "SHARD_ID" not in kwargs["env"]


def test_timeout_posts_failed_result_with_diagnostics():
    execution = {
        "duration_seconds": 10,
        "ramp_up_seconds": 0,
        "ramp_down_seconds": 0,
        "stop_policy": "hard_stop",
        "graceful_stop_seconds": 0,
        "max_run_seconds": 10,
        "iteration_limit": None,
        "data_policy": "duration_first",
    }
    timeout = subprocess.TimeoutExpired(cmd="k6", timeout=10, output="partial out", stderr="partial err")

    shard = sample_shard()

    with mock.patch.object(agent.subprocess, "run", side_effect=timeout), \
        mock.patch.object(agent, "calculate_k6_summary", return_value={"raw_report": {}}), \
        mock.patch.object(agent, "post_task_result") as post_mock, \
        mock.patch.object(agent, "push_summary_to_influxdb"):
        agent.execute_task(
            "task-4",
            "k6",
            "engines/k6/target_apps_payload_download.js",
            {"TARGET_URL": "http://target", "execution": execution, "shard": shard},
        )

    payload = post_mock.call_args.args[1]
    assert payload["execution_status"] == "failed"
    assert "max_run_seconds" in payload["error_message"]
    assert payload["raw_report"]["error"] == "worker_timeout"
    assert payload["raw_report"]["forced_stop"] is True
    assert payload["raw_report"]["shard"] == shard
    assert payload["raw_report"]["stdout"] == "partial out"
    assert payload["raw_report"]["stderr"] == "partial err"
    assert payload["artifact_manifest"]["artifact_manifest_version"] == "1.0"
    assert payload["artifact_manifest"]["items"][0]["artifact_id"] == "k6-summary-json"
