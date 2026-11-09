"""Simple rank-first search for P07's tiny English document corpus."""
import re
from simulate_tool_env import DOCS

STOP = {"a", "an", "and", "are", "for", "from", "in", "is", "of", "on", "the", "to", "what", "find", "official", "please", "look", "up"}

def terms(text):
    return [word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOP]

def matches(word, text_terms):
    # Tiny plural tolerance, not linguistic stemming or semantic retrieval.
    return word in text_terms or word + "s" in text_terms or word + "es" in text_terms

def ranked_search_docs(arguments):
    query = str(arguments.get("query", "")).strip()
    domain = arguments.get("domain")
    top_k = arguments.get("top_k", 3)
    if domain not in {"policy", "support", "billing", "security"}:
        return False, {"error_code": "invalid_domain"}
    if not query:
        return False, {"error_code": "empty_query"}
    if type(top_k) is not int or not 1 <= top_k <= 3:
        return False, {"error_code": "invalid_top_k"}
    query_terms = set(terms(query))
    if not query_terms:
        return False, {"error_code": "no_results"}
    scored = []
    for doc in DOCS:
        if doc["domain"] != domain:
            continue
        title_terms = set(terms(doc["title"]))
        body_terms = set(terms(doc["text"]))
        score = sum(3 * matches(term, title_terms) + matches(term, body_terms)
                    for term in query_terms)
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda item: (-item[0], item[1]["doc_id"]))
    if not scored:
        return False, {"error_code": "no_results"}
    return True, {"results": [{"doc_id": doc["doc_id"], "title": doc["title"],
                                "snippet": doc["text"]}
                               for _, doc in scored[:top_k]]}
