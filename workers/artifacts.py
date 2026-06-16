from __future__ import annotations

import hashlib
import json
from typing import Any


ARTIFACT_MANIFEST_VERSION = "1.0"

ARTIFACT_KIND_SUMMARY_JSON = "summary_json"
ARTIFACT_KIND_HTML_REPORT = "html_report"
ARTIFACT_KIND_JTL = "jtl"
ARTIFACT_KIND_STDOUT = "stdout"
ARTIFACT_KIND_STDERR = "stderr"
ARTIFACT_KIND_ENGINE_OUTPUT = "engine_output"
ARTIFACT_STATE_AVAILABLE = "available"
ARTIFACT_STATE_PLANNED = "planned"


def build_artifact_manifest(task_id: str, engine: str, execution_result: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "artifact_manifest_version": ARTIFACT_MANIFEST_VERSION,
        "items": build_artifact_manifest_entries(task_id, engine, execution_result),
    }


def build_artifact_manifest_entries(task_id: str, engine: str, execution_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    result = execution_result if isinstance(execution_result, dict) else {}
    raw_report = result.get("raw_report") if isinstance(result.get("raw_report"), dict) else {}
    artifact_evidence = result.get("artifact_evidence") if isinstance(result.get("artifact_evidence"), dict) else {}
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
                available=bool(artifact_evidence.get("has_summary_json")),
            ),
            _artifact_entry(
                task_id,
                artifact_id="k6-stdout",
                kind=ARTIFACT_KIND_STDOUT,
                name="stdout.txt",
                content_type="text/plain",
                available=stdout not in (None, ""),
                fingerprint_source=stdout,
            ),
            _artifact_entry(
                task_id,
                artifact_id="k6-stderr",
                kind=ARTIFACT_KIND_STDERR,
                name="stderr.txt",
                content_type="text/plain",
                available=stderr not in (None, ""),
                fingerprint_source=stderr,
            ),
            _artifact_entry(
                task_id,
                artifact_id="k6-engine-output",
                kind=ARTIFACT_KIND_ENGINE_OUTPUT,
                name="raw-report.json",
                content_type="application/json",
                available=has_raw_output,
                fingerprint_source=_stable_json_bytes(raw_report) if has_raw_output else None,
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
                available=bool(artifact_evidence.get("has_jtl")),
            ),
            _artifact_entry(
                task_id,
                artifact_id="jmeter-html-report",
                kind=ARTIFACT_KIND_HTML_REPORT,
                name="report.html",
                content_type="text/html",
                available=bool(artifact_evidence.get("has_html_report")),
            ),
            _artifact_entry(
                task_id,
                artifact_id="jmeter-stdout",
                kind=ARTIFACT_KIND_STDOUT,
                name="stdout.txt",
                content_type="text/plain",
                available=stdout not in (None, ""),
                fingerprint_source=stdout,
            ),
            _artifact_entry(
                task_id,
                artifact_id="jmeter-stderr",
                kind=ARTIFACT_KIND_STDERR,
                name="stderr.txt",
                content_type="text/plain",
                available=stderr not in (None, ""),
                fingerprint_source=stderr,
            ),
            _artifact_entry(
                task_id,
                artifact_id="jmeter-engine-output",
                kind=ARTIFACT_KIND_ENGINE_OUTPUT,
                name="raw-report.json",
                content_type="application/json",
                available=has_raw_output,
                fingerprint_source=_stable_json_bytes(raw_report) if has_raw_output else None,
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
            fingerprint_source=_stable_json_bytes(raw_report) if has_raw_output else None,
        )
    ]


def compute_safe_artifact_fingerprint(value: str | bytes | None) -> dict[str, Any]:
    if value in (None, ""):
        return {
            "size_bytes": None,
            "checksum_sha256": None,
        }
    payload = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(payload, (bytes, bytearray)):
        return {
            "size_bytes": None,
            "checksum_sha256": None,
        }
    digest = hashlib.sha256(bytes(payload)).hexdigest()
    return {
        "size_bytes": len(payload),
        "checksum_sha256": digest,
    }


def _artifact_entry(
    task_id: str,
    *,
    artifact_id: str,
    kind: str,
    name: str,
    content_type: str,
    available: bool,
    fingerprint_source: str | bytes | None = None,
) -> dict[str, Any]:
    state = ARTIFACT_STATE_AVAILABLE if available else ARTIFACT_STATE_PLANNED
    fingerprint = compute_safe_artifact_fingerprint(fingerprint_source) if available else {
        "size_bytes": None,
        "checksum_sha256": None,
    }
    return {
        "artifact_id": artifact_id,
        "kind": kind,
        "name": name,
        "state": state,
        "size_bytes": fingerprint["size_bytes"],
        "content_type": content_type,
        "object_ref": f"artifact://tasks/{task_id}/{artifact_id}" if available else None,
        "storage_backend": "worker_output",
        "checksum_sha256": fingerprint["checksum_sha256"],
        "provenance_source": "worker_output",
        "metadata": {},
    }


def _stable_json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
