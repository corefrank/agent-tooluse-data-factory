"""Offline deterministic tests, no embedding model or API needed."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rag.build_corpus import generate
from rag.chunk_corpus import build_all, chunk_document
from rag.bm25_baseline import BM25, tokenize
from rag.evaluate_retrieval import evaluate


class TestRAGPhase2A(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.questions, cls.manifest = generate()
        cls.chunks = build_all(cls.docs)

    def test_quantity_and_split(self):
        self.assertEqual(len(self.docs), 120)
        self.assertEqual(len(self.questions), 240)
        self.assertEqual(self.manifest["questions_by_split"], {"dev": 60, "test": 60, "train": 120})

    def test_reproducible(self):
        docs, questions, manifest = generate()
        self.assertEqual(self.docs, docs)
        self.assertEqual(self.questions, questions)
        self.assertEqual(self.manifest, manifest)

    def test_no_entity_leak(self):
        groups = {split: {q["task_group_id"] for q in self.questions if q["split"] == split}
                  for split in ("train", "dev", "test")}
        self.assertFalse(groups["train"] & groups["dev"])
        self.assertFalse(groups["dev"] & groups["test"])
        self.assertFalse(groups["train"] & groups["test"])

    def test_chunk_maps_to_original(self):
        by_id = {d["doc_id"]: d for d in self.docs}
        for c in self.chunks:
            self.assertEqual(c["text"], by_id[c["doc_id"]]["text"][c["start_char"]:c["end_char"]])
            self.assertLessEqual(len(c["text"]), 480)

    def test_gold_answer_in_at_least_one_chunk(self):
        lookup = {}
        for c in self.chunks:
            lookup.setdefault(c["doc_id"], []).append(c["text"])
        for q in self.questions:
            self.assertTrue(any(q["expected_answer"] in s for doc_id in q["gold_doc_ids"] for s in lookup[doc_id]), q["query_id"])

    def test_chunk_overlap_and_progress(self):
        for doc in self.docs:
            chunks = chunk_document(doc)
            self.assertEqual(chunks[0]["start_char"], 0)
            self.assertEqual(chunks[-1]["end_char"], len(doc["text"]))
            for a, b in zip(chunks, chunks[1:]):
                self.assertLess(a["start_char"], b["start_char"])
                self.assertLessEqual(b["start_char"], a["end_char"])

    def test_tokenizer(self):
        self.assertIn("gamma", tokenize("Gamma 产品退货期限是多久？"))
        self.assertIn("退货", tokenize("Gamma 产品退货期限是多久？"))

    def test_bm25_returns_doc_ids(self):
        bm25 = BM25(self.chunks)
        hits = bm25.search("Atlas return window", domain="policy")
        self.assertTrue(hits)
        self.assertTrue(all(h["domain"] == "policy" for h in hits))
        self.assertEqual(hits[0]["doc_id"], "kb_atlas_returns_v1")

    def test_eval_dev(self):
        result = evaluate(self.chunks, self.questions, "dev")
        self.assertEqual(result["summary"]["n_queries"], 60)
        self.assertGreaterEqual(result["summary"]["recall_at_1"], 0)
        self.assertLessEqual(result["summary"]["recall_at_1"], 1)

if __name__ == "__main__":
    unittest.main()
