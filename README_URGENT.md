# P07 — Real Agent MVP Add-on

Copy the `src/*.py` files into the existing P07 project `src/` (do not overwrite existing scripts). This package does not modify the original 13 checks or 94 records.

## 1. Setup

```bash
cd ~/projects/data_engineering_book/code/zh/project_7_agent_tooluse
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-agent.txt
python -m unittest discover -s src -p 'test_agent_mvp.py' -v
```

## 2. Connect a real LLM

### Option A: local open-weight Qwen3 model via Ollama

Make sure Ollama is installed/running and `ollama pull qwen3:4b-instruct` was successful. In WSL, Ollama may be running in Windows; check `curl http://localhost:11434/api/tags`.

```bash
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama
export AGENT_MODEL=qwen3:4b-instruct
```

### Option B: hosted Qwen / any compatible endpoint

```bash
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
read -rs -p 'API key: ' OPENAI_API_KEY; echo; export OPENAI_API_KEY
export AGENT_MODEL=qwen-plus
```

Match endpoint region with your key. Workspace-specific URLs are also supported. Hosted qwen-plus is an API model, not necessarily the same open-weight checkpoint as local Qwen3.

## 3. Run

```bash
python src/agent_mvp.py --split eval --variant both --limit 3
python src/agent_mvp.py --split eval --variant both
python src/agent_mvp.py --split train --variant enhanced
python src/export_agent_sft.py
```

Outputs are in `data/agent_mvp/`: eval_baseline.jsonl, eval_enhanced.jsonl, metric JSONs, train_enhanced.jsonl, train_enhanced_sft.jsonl.

## 4. What the metrics mean

- `task_success_rate`: share of cases passing a simple **rule-based evidence + answer** verifier; not semantic model correctness or BFCL score.
- `tool_execution_success_rate`: actual Python tool executor success, not tool-name selection accuracy.
- `passed_tasks`: count of cases passing the verifier.
- `mean_seconds`: local observed wall-clock per task.

The eval set comprises only 8 toy cases. `train` has 12 toy cases using the same underlying miniature database/docs, so it is a demonstration and **not a credible generalization benchmark**. Do not claim a robust percentage increase from such a tiny dataset; report `n=8`, actual results, and limitations. Cases have task IDs isolated, but share source facts.

## Important safety notes

This benchmark deliberately exposes only read-only search, single-account lookup, read-only calendar, and allowlisted session memory. Original P07 `python_exec` is NOT used (its in-process `exec` is not a robust sandbox). Unknown tool calls fail closed. Remote LLM tool calls may incur fees and send prompts / synthetic task data to the provider.

## Resume wording

- Adapted the P07 toy simulation into an actual model-driven tool-calling agent, using Qwen via an OpenAI-compatible client and a restricted executor for search, account lookup, calendar and memory operations.
- Implemented event-level traces, automated evidence-based verification, negative/safety regression tests, SFT-ready export with training/evaluation separation.
- Measured [actual] success rate on [n] small held-out tasks versus a baseline prompt; avoid claiming strong generalization or model performance gain without more substantial evaluation.

## 5. Compare identical evaluation tasks

```bash
python src/compare_agent_runs.py
```

This exports `data/agent_mvp/comparison.json` and shows task-level wins and regressions. **This comparison measures a prompt/guardrail intervention, not model training or the data filtering algorithm.**

### Offline safety/regression coverage

The package includes 13 deterministic `unittest` cases, including a CS329Z-inspired scripted client that exercises tool calling, failure recovery, and two-turn memory without any API calls. Start with these before configuring a model.

### WSL setup note

If creating the Python venv fails with `ensurepip` missing, use `uv venv .venv && source .venv/bin/activate && uv pip install -r requirements-agent.txt` (if you have `uv`) or install Ubuntu's `python3-venv` package.
