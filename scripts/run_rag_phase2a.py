"""Offline one-command corpus build, chunking, and dev BM25 evaluation."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from rag.build_corpus import generate, write_jsonl
from rag.chunk_corpus import build_all
from rag.evaluate_retrieval import evaluate


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, default=Path("data/rag"))
    p.add_argument("--chunk-size", type=int, default=480)
    p.add_argument("--overlap", type=int, default=70)
    args = p.parse_args()
    docs, questions, manifest = generate()
    chunks = build_all(docs, chunk_size=args.chunk_size, overlap=args.overlap)
    by_id = {d["doc_id"]: d for d in docs}
    assert all(c["text"] == by_id[c["doc_id"]]["text"][c["start_char"]:c["end_char"]] for c in chunks)
    assert all(any(q["expected_answer"] in c["text"] for c in chunks if c["doc_id"] in q["gold_doc_ids"]) for q in questions)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "documents.jsonl", docs)
    write_jsonl(args.out_dir / "questions.jsonl", questions)
    write_jsonl(args.out_dir / "chunks.jsonl", chunks)
    manifest["index_version"] = "bm25-" + hashlib.sha256(f"{manifest['corpus_sha256']}|chunk_size={args.chunk_size}|overlap={args.overlap}|splitter=boundary-v1|retriever=bm25-v1".encode()).hexdigest()[:16]
    manifest.update({"num_chunks": len(chunks), "chunk_size": args.chunk_size, "chunk_overlap": args.overlap,
                     "retrieval_stage": "phase2a-bm25-only", "structured_trace_env": "P07_INDEX_VERSION"})
    (args.out_dir / "corpus_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = evaluate(chunks, questions, split="dev")
    (args.out_dir / "bm25_dev_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"num_documents": len(docs), "num_chunks": len(chunks), "num_queries": len(questions),
                      "index_version": manifest["index_version"], "split_counts": manifest["questions_by_split"],
                      "bm25_dev_summary": report["summary"]}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
