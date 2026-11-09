"""Offline trace quality auditor: python3 scripts/audit_structured_traces.py PATH.jsonl"""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from structured_trace import audit_trace


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/audit_structured_traces.py path/to/traces.jsonl")
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print("File not found:", path)
        return 2
    seen = set()
    reasons = Counter()
    span_types = Counter()
    failures = 0
    count = 0
    bad = 0
    with path.open(encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            count += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"[INVALID JSON] line {line_num}: {exc}")
                bad += 1
                continue
            errors = audit_trace(record)
            run_id = record.get("run_id")
            if run_id in seen:
                errors.append("duplicate_run_id")
            seen.add(run_id)
            for s in record.get("spans", []) if isinstance(record.get("spans"), list) else []:
                span_types[s.get("kind", "unknown")] += 1
            if record.get("passed") is False:
                failures += 1
                for reason in record.get("failure_reasons", []):
                    reasons[reason.split(":", 1)[0]] += 1
            if errors:
                bad += 1
                print(f"[INVALID TRACE] line={line_num} task_id={record.get('task_id')} errors={errors}")
    print(f"Traces: {count}, invalid: {bad}, failed tasks: {failures}")
    print("Spans:", dict(span_types))
    print("Failure types:", dict(reasons))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
