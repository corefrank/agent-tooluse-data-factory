"""Export verified TRAIN trajectories only; never export eval traces for training."""
import argparse
import json
from pathlib import Path
from agent_mvp import OUTDIR, TOOLS

p = argparse.ArgumentParser()
p.add_argument("--variant", choices=["enhanced", "baseline"], default="enhanced")
args = p.parse_args()
source = OUTDIR / f"train_{args.variant}.jsonl"
if not source.exists():
    raise SystemExit(f"Missing {source}. First run: python src/agent_mvp.py --split train --variant {args.variant}")
records = [json.loads(s) for s in source.read_text(encoding="utf-8").splitlines() if s.strip()]
target = OUTDIR / f"train_{args.variant}_sft.jsonl"
with target.open("w", encoding="utf-8") as f:
    for r in records:
        if r["passed"]:
            f.write(json.dumps({"task_id": r["task_id"], "messages": r["messages"], "tools": TOOLS}, ensure_ascii=False) + "\n")
print(f"Exported {sum(r['passed'] for r in records)}/{len(records)} verified TRAIN conversations -> {target}")
print("Note: SFT-ready message schema, not proof of training success; never mix eval into training.")
