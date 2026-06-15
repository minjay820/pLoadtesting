import importlib.util
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
SPEC = importlib.util.spec_from_file_location("worker_agent", AGENT_PATH)
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


def completed_process(cmd):
    return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")


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

    with mock.patch.object(agent.subprocess, "run", side_effect=timeout), \
        mock.patch.object(agent, "calculate_k6_summary", return_value={"raw_report": {}}), \
        mock.patch.object(agent, "post_task_result") as post_mock, \
        mock.patch.object(agent, "push_summary_to_influxdb"):
        agent.execute_task(
            "task-4",
            "k6",
            "engines/k6/target_apps_payload_download.js",
            {"TARGET_URL": "http://target", "execution": execution},
        )

    payload = post_mock.call_args.args[1]
    assert payload["execution_status"] == "failed"
    assert "max_run_seconds" in payload["error_message"]
    assert payload["raw_report"]["error"] == "worker_timeout"
    assert payload["raw_report"]["forced_stop"] is True
    assert payload["raw_report"]["stdout"] == "partial out"
    assert payload["raw_report"]["stderr"] == "partial err"
