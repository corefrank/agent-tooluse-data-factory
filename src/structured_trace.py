"""Structured Trace v1: shared, standard-library-only trace helpers.

No network calls. Existing JSONL and messages formats remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

TRACE_SCHEMA_VERSION = "1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_json(data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def start_trace(*, task: dict, model: str, prompt: str, harness: str = "custom") -> dict:
    """Identifiers and configuration snapshot. No raw API credentials are retained.

    task_sha256 identifies only the Task Spec, NOT knowledge-base fixture versions.
    Specify P07_INDEX_VERSION when changing the corpus/index.
    """
    return {
        "trace_schema_version": TRACE_SCHEMA_VERSION,
        "run_id": uuid.uuid4().hex,
        "experiment_id": os.getenv("P07_EXPERIMENT_ID", "unassigned"),
        "harness": harness,
        "started_at": utc_now(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "task_sha256": sha256_json(task),
        "retriever": os.getenv("P07_RETRIEVER", "original"),
        "index_version": os.getenv("P07_INDEX_VERSION", "unversioned"),
        "model_config": {"model": model, "temperature": 0, "tool_choice": "auto"},
    }


def response_usage(response: Any) -> dict | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        return {k: usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens") if k in usage}
    return {k: getattr(usage, k) for k in ("prompt_tokens", "completion_tokens", "total_tokens") if getattr(usage, k, None) is not None}


def audit_trace(record: dict) -> list[str]:
    """Check trace structure and tool-call/result pairing; never rewrite data."""
    errors = []
    for key in ("trace_schema_version", "run_id", "task_id", "model", "prompt_sha256", "task_sha256", "retriever", "started_at", "spans", "events", "messages"):
        if key not in record:
            errors.append("missing:" + key)
    if not isinstance(record.get("spans", []), list):
        errors.append("spans_not_list")
    for span in record.get("spans", []) if isinstance(record.get("spans", []), list) else []:
        if span.get("latency_ms", 0) < 0:
            errors.append("negative_latency")
    calls = []
    tool_results = []
    for m in record.get("messages", []):
        if m.get("role") == "assistant":
            calls.extend(str(tc.get("id")) for tc in m.get("tool_calls", []))
        if m.get("role") == "tool":
            tool_results.append(str(m.get("tool_call_id")))
    if sorted(calls) != sorted(tool_results):
        errors.append("tool_call_response_mismatch")
    return errors
