"""Offline smoke test for the newly patched Custom Harness. Never calls an API."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent_mvp import EVAL_TASKS, ENHANCED_PROMPT, run_task
from structured_trace import audit_trace


class FakeClient:
    def __init__(self):
        self.count = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.count += 1
        if self.count == 1:
            call = SimpleNamespace(id="call_smoke_1", function=SimpleNamespace(
                name="search_docs", arguments=json.dumps({"query": "refund", "domain": "policy", "top_k": 2})))
            message = SimpleNamespace(content=None, tool_calls=[call])
        else:
            message = SimpleNamespace(content="Refunds are available within 30 days of purchase.", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)


client = FakeClient()
record = run_task(client, "fake-model", EVAL_TASKS[0], ENHANCED_PROMPT)
assert record["passed"], record["failure_reasons"]
assert record["tool_calls"] == 1
assert len(record["run_id"]) == 32
assert len(record["spans"]) == 3
assert [s["kind"] for s in record["spans"]] == ["llm", "tool", "llm"]
assert record["events"][2]["type"] == "tool"  # Preserve legacy event order
assert record["events"][2]["call_id"] == "call_smoke_1"
assert record["events"][2]["latency_ms"] >= 0
assert not audit_trace(record), audit_trace(record)
assert "OPENAI_API_KEY" not in json.dumps(record)
output = ROOT / "data" / "agent_mvp" / "structured_trace_smoke.jsonl"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
print("PASS: Structured Trace v1, API-free FakeClient test")
print("Saved demo trace:", output)
print(json.dumps({k: record[k] for k in ("run_id", "task_id", "model", "retriever", "started_at", "prompt_sha256", "index_version")}, ensure_ascii=False, indent=2))
print("spans:", [(s["kind"], s["latency_ms"], s["ok"]) for s in record["spans"]])
