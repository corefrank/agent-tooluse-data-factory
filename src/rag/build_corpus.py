"""Generate a labeled, entirely synthetic enterprise knowledge base.

No LLM/API calls. No real customers or secret data. Outputs are deterministic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

BRANDS = (
    "Atlas", "Aurora", "Boreal", "Cobalt", "Delta", "Echo", "Falcon", "Gamma",
    "Helix", "Indigo", "Jasper", "Kepler", "Lumen", "Meridian", "Nimbus", "Orion",
    "Pioneer", "Quartz", "Riverton", "Solstice", "Tandem", "Umbra", "Vantage", "Willow",
)
TOPICS = ("returns", "renewals", "seats", "support", "security")
DOMAIN = {"returns": "policy", "renewals": "policy", "seats": "billing", "support": "support", "security": "security"}
DOC_VERSION = "p07-synthetic-enterprise-1.0"
# Split by brand/entity, not randomly by question. This reduces template/entity leakage.
SPLIT = {name: ("train" if i < 12 else "dev" if i < 18 else "test") for i, name in enumerate(BRANDS)}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records), encoding="utf-8")


def content_for(brand: str, brand_i: int, topic: str) -> tuple[str, str, str]:
    # 'answer' always appears in the document fact block, not only in gold metadata.
    days = [14, 21, 30, 45, 60][brand_i % 5]
    delay = [7, 10, 14, 21, 28][brand_i % 5]
    seats = 12 + (brand_i * 7) % 89
    response = [2, 4, 8, 12, 24][brand_i % 5]
    session = [15, 20, 30, 45, 60][brand_i % 5]
    email = brand.lower() + "-support@example.invalid"
    facts = {
        "returns": (f"{days} days", f"The current {brand} product return window is {days} days after verified delivery. "
                    "A return request must include the order identifier and delivery confirmation. "
                    "A quoted period from another brand does not override this rule."),
        "renewals": (f"{delay} days", f"A {brand} subscription renewal may be postponed by up to {delay} days, "
                     "but only if the account owner files the request before the billing cutoff. "
                     "Requests after the cutoff require manual case review."),
        "seats": (f"{seats} named seats", f"The current {brand} Team plan includes exactly {seats} named seats. "
                  "Temporary guests are not counted as named seats, and purchased add-ons are listed separately. "
                  "Do not confuse the Team allowance with Enterprise tiers."),
        "support": (email, f"For {brand} account support, the approved contact email address is {email}. "
                    f"The initial response target for standard {brand} tickets is {response} business hours. "
                    "Escalation requests must provide the customer ticket ID."),
        "security": (f"{session} minutes", f"The {brand} console automatically ends an idle administrator session after {session} minutes. "
                     "Multi-factor authentication is required for administrator access. "
                     "An idle session cannot be renewed using an unverified browser token."),
    }
    answer, fact = facts[topic]
    title = {
        "returns": "Product Returns and Refund Requests",
        "renewals": "Subscription Renewal Postponement",
        "seats": "Team Plan Named-Seat Entitlement",
        "support": "Enterprise and Account Support Contacts",
        "security": "Administrator Session Security Standard",
    }[topic]
    return title, answer, fact


def make_document(brand: str, brand_i: int, topic: str) -> dict:
    topic_title, answer, fact = content_for(brand, brand_i, topic)
    doc_id = f"kb_{brand.lower()}_{topic}_v1"
    # The fact is in a standalone paragraph so at least one chunk carries its exact answer.
    paras = [
        f"{brand} — {topic_title}. CURRENT REFERENCE DOCUMENT. Section 1: Scope.",
        f"This internal reference applies to the {brand} product family only. It must not be used "
        f"to infer eligibility for another vendor or a different contract. Domain: {DOMAIN[topic]}. "
        "The content is a fictional demonstration for retrieval evaluation; no customer data is present.",
        f"Section 2: Controlling rule. {fact}",
        f"Section 3: Operational process. A support specialist first checks that the request identifies the "
        f"{brand} product line and the current applicable document version. A case note records the request "
        "date, document identifier, cited excerpt, and disposition so that reviewers can audit the decision.",
        f"Section 4: Similar but non-equivalent policies. The rule for {brand} {topic} must not be inferred "
        "from a general company FAQ, from a different topic, or from a competing product family. "
        "If a query omits the product identifier, ask for clarification before assuming the answer.",
        f"Section 5: Version control. This policy is current from 2026-10-{(brand_i % 24) + 1:02d}. "
        "A superseded summary may be retained for history, but current references control the answer. "
        f"Auditors should link back to {doc_id}, and preserve the retrieved chunk identifiers.",
    ]
    text = "\n\n".join(paras)
    return {
        "doc_id": doc_id,
        "title": f"{brand} | {topic_title}",
        "domain": DOMAIN[topic],
        "brand": brand,
        "topic": topic,
        "effective_date": f"2026-10-{(brand_i % 24) + 1:02d}",
        "version": "v1",
        "source_type": "synthetic",
        "corpus_version": DOC_VERSION,
        "text": text,
        "content_sha256": sha(text),
    }


def make_question(brand: str, topic: str, i: int, variant: int) -> str:
    english = {
        "returns": f"What is the current {brand} product return window after delivery?",
        "renewals": f"How many days may a {brand} subscription renewal be postponed?",
        "seats": f"How many named seats are included in the {brand} Team plan?",
        "support": f"What is the approved {brand} customer support email address?",
        "security": f"After how many minutes does an idle {brand} administrator session expire?",
    }
    chinese = {
        "returns": f"{brand} 产品收货后，现行退货期限是多久？",
        "renewals": f"{brand} 订阅续费最多可以延后多少天？",
        "seats": f"{brand} 团队版套餐包含几个正式席位？",
        "support": f"请告诉我 {brand} 的官方账户客服邮箱。",
        "security": f"{brand} 管理员长时间无操作后多少分钟自动退出？",
    }
    return (english if variant == 0 else chinese)[topic]


def generate() -> tuple[list[dict], list[dict], dict]:
    docs = [make_document(name, i, topic) for i, name in enumerate(BRANDS) for topic in TOPICS]
    questions = []
    for i, name in enumerate(BRANDS):
        for j, topic in enumerate(TOPICS):
            title, answer, _ = content_for(name, i, topic)
            # Evaluate both English and Chinese paraphrases across all five categories.
            for variant in range(2):
                questions.append({
                    "query_id": f"q_{name.lower()}_{topic}_{'en' if variant == 0 else 'zh'}",
                    "task_group_id": f"brand_{name.lower()}",
                    "split": SPLIT[name],
                    "language": "en" if variant == 0 else "zh",
                    "query": make_question(name, topic, i, variant),
                    "domain": DOMAIN[topic],
                    "gold_doc_ids": [f"kb_{name.lower()}_{topic}_v1"],
                    "expected_answer": answer,
                    "entity": name,
                    "topic": topic,
                })
    docs.sort(key=lambda x: x["doc_id"])
    questions.sort(key=lambda x: x["query_id"])
    digest = sha("\n".join(d["doc_id"] + ":" + d["content_sha256"] for d in docs))
    manifest = {
        "corpus_version": DOC_VERSION,
        "index_version": f"corpus-{digest[:16]}",
        "corpus_sha256": digest,
        "source_type": "synthetic",
        "seed": "fixed-rule-v1",
        "num_documents": len(docs),
        "num_questions": len(questions),
        "documents_by_domain": dict(sorted(Counter(d["domain"] for d in docs).items())),
        "questions_by_split": dict(sorted(Counter(q["split"] for q in questions).items())),
        "questions_by_language": dict(sorted(Counter(q["language"] for q in questions).items())),
        "split_strategy": "group by brand; 12 train / 6 dev / 6 test entities",
        "generation_note": "Synthetic benchmark, no real-world policy claims, labels generated from the same templates as docs.",
    }
    return docs, questions, manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, default=Path("data/rag"))
    args = p.parse_args()
    docs, questions, manifest = generate()
    write_jsonl(args.out_dir / "documents.jsonl", docs)
    write_jsonl(args.out_dir / "questions.jsonl", questions)
    (args.out_dir / "corpus_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
