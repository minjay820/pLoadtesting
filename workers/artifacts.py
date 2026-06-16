from __future__ import annotations

from typing import Any


ARTIFACT_KIND_SUMMARY_JSON = "summary_json"
ARTIFACT_KIND_HTML_REPORT = "html_report"
ARTIFACT_KIND_JTL = "jtl"
ARTIFACT_KIND_STDOUT = "stdout"
ARTIFACT_KIND_STDERR = "stderr"
ARTIFACT_KIND_ENGINE_OUTPUT = "engine_output"
ARTIFACT_STATE_AVAILABLE = "available"
ARTIFACT_STATE_PLANNED = "planned"


def build_artifact_manifest_entries(task_id: str, engine: str, execution_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    result = execution_result if isinstance(execution_result, dict) else {}
    raw_report = result.get("raw_report") if isinstance(result.get("raw_report"), dict) else {}
    stdout = raw_report.get("stdout")
    stderr = raw_report.get("stderr")
    has_raw_output = bool(raw_report)

    if engine == "k6":
        return [
            _artifact_entry(
                task_id,
                artifact_id="k6-summary-json",
                kind=ARTIFACT_KIND_SUMMARY_JSON,
                name="summary.json",
                content_type="application/json",
                available=bool(result.get("artifact_evidence", {}).get("has_summary_json")),
            ),
            _artifact_entry(
                task_id,
                artifact_id="k6-stdout",
                kind=ARTIFACT_KIND_STDOUT,
                name="stdout.txt",
                content_type="text/plain",
                available=stdout not in (None, ""),
            ),
            _artifact_entry(
                task_id,
                artifact_id="k6-stderr",
                kind=ARTIFACT_KIND_STDERR,
                name="stderr.txt",
                content_type="text/plain",
                available=stderr not in (None, ""),
            ),
            _artifact_entry(
                task_id,
                artifact_id="k6-engine-output",
                kind=ARTIFACT_KIND_ENGINE_OUTPUT,
                name="raw-report.json",
                content_type="application/json",
                available=has_raw_output,
            ),
        ]

    if engine == "jmeter":
        return [
            _artifact_entry(
                task_id,
                artifact_id="jmeter-jtl",
                kind=ARTIFACT_KIND_JTL,
                name="results.jtl",
                content_type="text/csv",
                available=bool(result.get("artifact_evidence", {}).get("has_jtl")),
            ),
            _artifact_entry(
                task_id,
                artifact_id="jmeter-html-report",
                kind=ARTIFACT_KIND_HTML_REPORT,
                name="report.html",
                content_type="text/html",
                available=bool(result.get("artifact_evidence", {}).get("has_html_report")),
            ),
            _artifact_entry(
                task_id,
                artifact_id="jmeter-stdout",
                kind=ARTIFACT_KIND_STDOUT,
                name="stdout.txt",
                content_type="text/plain",
                available=stdout not in (None, ""),
            ),
            _artifact_entry(
                task_id,
                artifact_id="jmeter-stderr",
                kind=ARTIFACT_KIND_STDERR,
                name="stderr.txt",
                content_type="text/plain",
                available=stderr not in (None, ""),
            ),
            _artifact_entry(
                task_id,
                artifact_id="jmeter-engine-output",
                kind=ARTIFACT_KIND_ENGINE_OUTPUT,
                name="raw-report.json",
                content_type="application/json",
                available=has_raw_output,
            ),
        ]

    return [
        _artifact_entry(
            task_id,
            artifact_id="engine-output",
            kind=ARTIFACT_KIND_ENGINE_OUTPUT,
            name="raw-report.json",
            content_type="application/json",
            available=has_raw_output,
        )
    ]


def _artifact_entry(
    task_id: str,
    *,
    artifact_id: str,
    kind: str,
    name: str,
    content_type: str,
    available: bool,
) -> dict[str, Any]:
    state = ARTIFACT_STATE_AVAILABLE if available else ARTIFACT_STATE_PLANNED
    return {
        "artifact_id": artifact_id,
        "kind": kind,
        "name": name,
        "state": state,
        "size_bytes": None,
        "content_type": content_type,
        "object_ref": f"artifact://tasks/{task_id}/{artifact_id}" if available else None,
        "storage_backend": "worker_output",
        "checksum_sha256": None,
        "provenance_source": "worker_output",
        "metadata": {},
    }
