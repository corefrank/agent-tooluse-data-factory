from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
TRAINING_DIR = DATA_DIR / "training"
REPORTS_DIR = DATA_DIR / "reports"


def ensure_standard_dirs() -> None:
    for path in [DATA_DIR, PROCESSED_DIR, TRAINING_DIR, REPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def write_json(data: dict | list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(records: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def deterministic_bucket(value: str, mod: int = 100) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % mod


def estimated_tokens(text: str) -> int:
    return max(1, len(text.split()))
