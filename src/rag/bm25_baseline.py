"""Dependency-free, auditable BM25 chunk retriever (not a production tokenizer).

Indexes each chunk and its title; uses simple Latin tokens and CJK character bigrams.
This is a sparse baseline for future Qdrant dense/hybrid experiments.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Iterable

LATIN = re.compile(r"[a-z0-9]+", flags=re.I)
CJK = re.compile(r"[\u3400-\u9fff]+")
STOP = {"a", "an", "and", "the", "to", "is", "what", "how", "after", "for", "in", "of", "are", "please", "tell", "me", "current", "can", "be", "by", "from", "does", "at", "that", "up", "with", "it", "do", "our", "you", "your"}


def tokenize(text: str) -> list[str]:
    english = [m.group(0).lower() for m in LATIN.finditer(text) if m.group(0).lower() not in STOP]
    cjk = []
    for match in CJK.finditer(text):
        span = match.group(0)
        cjk.extend(span[i:i+2] for i in range(len(span) - 1))
        if len(span) == 1:
            cjk.append(span)
    return english + cjk


class BM25:
    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75, title_weight: int = 2):
        if not chunks:
            raise ValueError("Need non-empty chunks")
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.terms = []
        self.df = Counter()
        self.domain_indices = defaultdict(list)
        for i, chunk in enumerate(chunks):
            # Deliberately simple, repeated title terms give title a small boost.
            terms = tokenize(chunk["text"]) + tokenize(chunk["title"]) * title_weight
            freq = Counter(terms)
            self.terms.append(freq)
            self.df.update(freq.keys())
            self.domain_indices[chunk["domain"]].append(i)
        self.n = len(self.terms)
        self.avdl = sum(sum(t.values()) for t in self.terms) / self.n

    def search(self, query: str, top_k: int = 10, domain: str | None = None) -> list[dict]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        terms = set(tokenize(query))
        scored = []
        candidate_ids = self.domain_indices.get(domain, []) if domain else range(self.n)
        for idx in candidate_ids:
            freq = self.terms[idx]
            dl = sum(freq.values())
            s = 0.0
            for term in terms:
                tf = freq.get(term, 0)
                if not tf:
                    continue
                df = self.df[term]
                idf = math.log(1 + (self.n - df + 0.5) / (df + 0.5))
                s += idf * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avdl))
            if s > 0:
                c = self.chunks[idx]
                scored.append({"doc_id": c["doc_id"], "chunk_id": c["chunk_id"], "title": c["title"],
                               "domain": c["domain"], "snippet": c["text"], "score": round(s, 8)})
        scored.sort(key=lambda d: (-d["score"], d["chunk_id"]))
        return scored[:top_k]


def distinct_documents(chunk_hits: Iterable[dict]) -> list[str]:
    seen = set()
    ids = []
    for item in chunk_hits:
        doc_id = item["doc_id"]
        if doc_id not in seen:
            seen.add(doc_id)
            ids.append(doc_id)
    return ids
