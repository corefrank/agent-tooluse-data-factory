"""Labeled document-retrieval evaluation. Only dev by default.

A document counts as retrieved when any of its chunks appears in the ranked
results, after deduplicating chunk hits to unique document IDs.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

try:
    from .bm25_baseline import BM25, distinct_documents
    from .chunk_corpus import read_jsonl
except ImportError:  # direct `python src/rag/evaluate_retrieval.py`
    from bm25_baseline import BM25, distinct_documents
    from chunk_corpus import read_jsonl


def evaluate(chunks: list[dict], queries: list[dict], split: str, top_k: int = 10) -> dict:
    if split not in {"train", "dev", "test"}:
        raise ValueError("split must be train/dev/test")
    bm25 = BM25(chunks)
    selected = [q for q in queries if q["split"] == split]
    if not selected:
        raise ValueError(f"No queries for {split}")
    details = []
    for q in selected:
        # Request extra chunk candidates, then deduplicate to document-level ranking.
        candidates = bm25.search(q["query"], domain=q["domain"], top_k=top_k * 6)
        docs = distinct_documents(candidates)[:top_k]
        gold = set(q["gold_doc_ids"])
        rank = next((i + 1 for i, d in enumerate(docs) if d in gold), None)
        details.append({"query_id": q["query_id"], "language": q["language"], "topic": q["topic"],
                        "split": split, "query": q["query"], "gold_doc_ids": q["gold_doc_ids"],
                        "rank": rank, "top_doc_ids": docs[:5]})
    n = len(details)
    summary = {
        "retriever": "bm25-simple-latin-cjk2gram",
        "split": split, "n_queries": n, "n_documents": len({c["doc_id"] for c in chunks}),
        "n_chunks": len(chunks),
        "recall_at_1": round(sum(d["rank"] is not None and d["rank"] <= 1 for d in details) / n, 4),
        "recall_at_5": round(sum(d["rank"] is not None and d["rank"] <= 5 for d in details) / n, 4),
        "mrr_at_10": round(sum(1 / d["rank"] if d["rank"] and d["rank"] <= 10 else 0 for d in details) / n, 4),
        "by_language": {},
    }
    for language in ("en", "zh"):
        matches = [d for d in details if d["language"] == language]
        summary["by_language"][language] = {
            "count": len(matches),
            "recall_at_1": round(sum(d["rank"] == 1 for d in matches) / len(matches), 4) if matches else None,
        }
    return {"summary": summary, "details": details}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path("data/rag"))
    p.add_argument("--split", choices=("train", "dev", "test"), default="dev")
    p.add_argument("--top-k", type=int, default=10)
    args = p.parse_args()
    if args.split == "test":
        print("NOTE: test split is reserved for final evaluation. Do not tune on its failures.")
    result = evaluate(read_jsonl(args.data_dir / "chunks.jsonl"), read_jsonl(args.data_dir / "questions.jsonl"), args.split, args.top_k)
    target = args.data_dir / f"bm25_{args.split}_report.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print("Report:", target)

if __name__ == "__main__":
    main()
