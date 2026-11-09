"""Install Structured Trace v1 into the CURRENT P07 Agent Harness.

Run from project root after unzipping the package. Does not call Qwen,
modify existing JSONL, or overwrite the original unpatched source backup.
"""
from pathlib import Path
import shutil

agent = Path("src/agent_mvp.py")
helper = Path("src/structured_trace.py")
if not agent.is_file() or not helper.is_file():
    raise SystemExit("Run from the P07 project root containing src/agent_mvp.py and src/structured_trace.py")

old = agent.read_text(encoding="utf-8")
if '"trace_schema_version": trace_meta["trace_schema_version"]' in old:
    print("Structured Trace v1 already installed. No changes made.")
    raise SystemExit(0)

anchors = [
    ('from typing import Any\n',
     'from typing import Any\n\nfrom structured_trace import start_trace, utc_now, response_usage\n'),
    ('    messages: list[dict] = [{"role": "system", "content": prompt}]\n',
     '    trace_meta = start_trace(task=task, model=model, prompt=prompt)\n'
     '    spans: list[dict] = []\n'
     '    messages: list[dict] = [{"role": "system", "content": prompt}]\n'),
    ('        for _ in range(max_steps):\n            try:\n',
     '        for _ in range(max_steps):\n'
     '            _llm_t0 = time.perf_counter()\n'
     '            _llm_started = utc_now()\n'
     '            try:\n'),
    ('                message = response.choices[0].message\n',
     '                message = response.choices[0].message\n'
     '                spans.append({"kind": "llm", "started_at": _llm_started, "ended_at": utc_now(),\n'
     '                              "latency_ms": round((time.perf_counter() - _llm_t0) * 1000, 3),\n'
     '                              "turn": turn_index, "ok": True, "usage": response_usage(response)})\n'),
    ('            except Exception as exc:\n                failure = type(exc).__name__ + ": " + str(exc)[:250]\n',
     '            except Exception as exc:\n'
     '                spans.append({"kind": "llm", "started_at": _llm_started, "ended_at": utc_now(),\n'
     '                              "latency_ms": round((time.perf_counter() - _llm_t0) * 1000, 3),\n'
     '                              "turn": turn_index, "ok": False, "error_type": type(exc).__name__})\n'
     '                failure = type(exc).__name__ + ": " + str(exc)[:250]\n'),
    ('                ok, observation = dispatch(tc.function.name, args, memory)\n',
     '                _tool_t0 = time.perf_counter()\n'
     '                _tool_started = utc_now()\n'
     '                ok, observation = dispatch(tc.function.name, args, memory)\n'
     '                _tool_ms = round((time.perf_counter() - _tool_t0) * 1000, 3)\n'
     '                spans.append({"kind": "tool", "started_at": _tool_started, "ended_at": utc_now(),\n'
     '                              "latency_ms": _tool_ms, "turn": turn_index, "call_id": tc.id,\n'
     '                              "tool_name": tc.function.name, "ok": ok})\n'),
    ('                events.append({"type": "tool", "turn": turn_index, "name": tc.function.name,\n                               "arguments": args, "ok": ok, "output": observation})\n',
     '                events.append({"type": "tool", "turn": turn_index, "name": tc.function.name,\n'
     '                               "arguments": args, "ok": ok, "output": observation,\n'
     '                               "call_id": tc.id, "timestamp": _tool_started, "latency_ms": _tool_ms})\n'),
    ('    return {"task_id": task["id"], "model": model, "passed": passed, "failure_reasons": reasons,\n',
     '    return {"trace_schema_version": trace_meta["trace_schema_version"],\n'
     '            "run_id": trace_meta["run_id"], "experiment_id": trace_meta["experiment_id"],\n'
     '            "harness": trace_meta["harness"], "started_at": trace_meta["started_at"],\n'
     '            "ended_at": utc_now(), "prompt_sha256": trace_meta["prompt_sha256"],\n'
     '            "task_sha256": trace_meta["task_sha256"], "retriever": trace_meta["retriever"],\n'
     '            "index_version": trace_meta["index_version"], "model_config": trace_meta["model_config"],\n'
     '            "spans": spans,\n'
     '            "task_id": task["id"], "model": model, "passed": passed, "failure_reasons": reasons,\n'),
]
updated = old
for before, after in anchors:
    if updated.count(before) != 1:
        raise SystemExit("Could not locate a unique patch anchor; NO changes were made: " + repr(before[:110]))
    updated = updated.replace(before, after, 1)
compile(updated, str(agent), "exec")
backup = agent.with_name("agent_mvp.py.before_structured_trace")
if not backup.exists():
    shutil.copy2(agent, backup)
agent.write_text(updated, encoding="utf-8")
print("Structured Trace v1 installed. Backup:", backup)
print("Old JSONL files untouched; run a NEW Agent task to capture real timings.")
