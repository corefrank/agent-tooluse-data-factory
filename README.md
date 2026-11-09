# P07 Structured Trace v1 (Phase 1)

Add trace metadata and per-call timing to the existing custom Qwen Harness **without adding an LLM framework or calling the API during install/tests**.

## Installation in WSL

From `~/projects/data_engineering_book/code/zh/project_7_agent_tooluse`:

```bash
unzip -o P07_structured_trace_phase1.zip
python3 install_structured_trace.py
python3 -m py_compile src/agent_mvp.py src/structured_trace.py
python3 scripts/smoke_structured_trace.py
python3 scripts/audit_structured_traces.py data/agent_mvp/structured_trace_smoke.jsonl
python3 src/test_agent_mvp.py
```

The offline smoke test saves a separate `data/agent_mvp/structured_trace_smoke.jsonl`, without overwriting any existing experiment.

To capture one **real** live task with the existing configuration (consumes model API quota):

```bash
export P07_EXPERIMENT_ID="trace-v1-smoke"
export P07_INDEX_VERSION="toy-docs-5-v1"
P07_RETRIEVER=ranked python3 src/agent_mvp.py --split eval --variant enhanced --limit 1
```

The last command **overwrites** `data/agent_mvp/eval_enhanced.jsonl` per the original benchmark script: **back up existing file first** if you want to retain the old results.

Recommended first, without paid model calls, inspect the output of the smoke script instead.

## New per-task fields

- `trace_schema_version`, `run_id`, `experiment_id`, `harness`
- `started_at`, `ended_at`, `prompt_sha256`, `task_sha256`
- `retriever`, `index_version`, `model_config`
- `spans`: ordered LLM and tool spans with start/end UTC times and latency

Existing `task_id`, `model`, `events`, `messages`, `failure_reasons`, `passed`, `seconds` are retained.
Tool events now have `call_id`, `timestamp`, and `latency_ms`.

## Limits

- `temperature=0` does not guarantee exact determinism of remote model outputs.
- `task_sha256` covers the task spec, **not the knowledge base**; set `P07_INDEX_VERSION` when corpus/index changes.
- Previously collected traces **cannot retroactively gain true per-step timestamps and durations**.
- The existing `messages`/`events` logs contain raw user input and tool outputs; redact personal information and secrets before sharing, and do not log API keys. No full production tracing, distributed context propagation or OpenTelemetry backend is implemented here.
- The existing model client is used unchanged, including its retry and error behavior.

## After this phase

Use the same schema for (1) Custom Harness + Ranked, (2) Custom Harness + Hybrid Retrieval, (3) LangGraph + Hybrid Retrieval. That enables a meaningful comparison of retrieval quality, agent quality, and fault recovery without conflating all changes.
