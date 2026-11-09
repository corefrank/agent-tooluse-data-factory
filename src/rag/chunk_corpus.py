"""Provenance-preserving character chunks; each chunk maps exactly to original text.

Text splitting uses paragraph/sentence boundary preference but never edits text.
Not a tokenizer or semantic splitter. Optional later swap: LangChain splitter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def boundaries(text: str, start: int, limit: int, chunk_size: int) -> int:
    if limit == len(text):
        return limit
    # Prefer a natural boundary late in the window, without losing source offsets.
    min_break = start + int(chunk_size * 0.62)
    choices = ("\n\n", ". ", "。", "; ", ", ", " ")
    for token in choices:
        pos = text.rfind(token, min_break, limit)
        if pos != -1:
            return pos + len(token)
    return limit


def chunk_document(doc: dict, chunk_size: int = 480, overlap: int = 70) -> list[dict]:
    if not 0 <= overlap < chunk_size:
        raise ValueError("Require 0 <= overlap < chunk_size")
    text = doc["text"]
    start = 0
    chunks = []
    while start < len(text):
        limit = min(len(text), start + chunk_size)
        end = boundaries(text, start, limit, chunk_size)
        if end <= start:
            end = limit
        chunk_text = text[start:end]
        ix = len(chunks)
        chunks.append({
            "chunk_id": f"{doc['doc_id']}__c{ix:03d}",
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "brand": doc["brand"],
            "domain": doc["domain"],
            "topic": doc["topic"],
            "source_type": doc["source_type"],
            "corpus_version": doc["corpus_version"],
            "version": doc["version"],
            "effective_date": doc["effective_date"],
            "start_char": start,
            "end_char": end,
            "text": chunk_text,
            "content_sha256": hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
        })
        if end == len(text):
            break
        new_start = max(0, end - overlap)
        if new_start <= start:
            new_start = end  # guaranteed progress
        start = new_start
    return chunks


def build_all(docs: list[dict], chunk_size: int = 480, overlap: int = 70) -> list[dict]:
    return [c for doc in docs for c in chunk_document(doc, chunk_size, overlap)]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path("data/rag"))
    p.add_argument("--chunk-size", type=int, default=480)
    p.add_argument("--overlap", type=int, default=70)
    args = p.parse_args()
    docs = read_jsonl(args.data_dir / "documents.jsonl")
    chunks = build_all(docs, args.chunk_size, args.overlap)
    target = args.data_dir / "chunks.jsonl"
    target.write_text("".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in chunks), encoding="utf-8")
    info = {
        "num_documents": len(docs), "num_chunks": len(chunks),
        "chunk_size": args.chunk_size, "overlap": args.overlap,
        "chunk_source_verified": all(
            c["text"] == next(d["text"] for d in docs if d["doc_id"] == c["doc_id"])[c["start_char"]:c["end_char"]]
            for c in chunks
        )
    }
    (args.data_dir / "chunk_manifest.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
