"""Print top failed BM25 dev queries; no API calls and no tuning on test."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path("data/rag"))
    p.add_argument("--limit", type=int, default=12)
    args = p.parse_args()
    path = args.data_dir / "bm25_dev_report.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    errors = [q for q in result["details"] if q["rank"] != 1]
    print(f"Dev queries: {len(result['details'])}; not top1: {len(errors)}")
    for q in errors[:args.limit]:
        print("\nQUERY", q["query_id"], "language=", q["language"])
        print("QUESTION", q["query"])
        print("GOLD", q["gold_doc_ids"])
        print("RANK", q["rank"])
        print("TOP5", q["top_doc_ids"])

if __name__ == "__main__":
    main()
