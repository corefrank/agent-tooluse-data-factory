"""Patch the P07 Agent MVP non-destructively to support optional ranked retrieval.
Place next to src/ in the P07 repository root, then run python3 install_ranked_retrieval.py.
"""
from pathlib import Path
import shutil

root = Path.cwd()
module = root / 'src' / 'ranked_retrieval.py'
if not module.is_file():
    raise SystemExit('First copy ranked_retrieval.py to src/ranked_retrieval.py')

agent = root / 'src' / 'agent_mvp.py'
holdout = root / 'src' / 'p07_holdout_benchmark.py'
if not agent.is_file() or not holdout.is_file():
    raise SystemExit('Must run from the P07 root with agent_mvp.py and p07_holdout_benchmark.py in src/')

s = agent.read_text(encoding='utf-8')
anchor='ROOT = Path(__file__).resolve().parent.parent'
needle='return search_docs(args)'
replacement='return ranked_search_docs(args) if os.getenv("P07_RETRIEVER") == "ranked" else search_docs(args)'
if 'from ranked_retrieval import ranked_search_docs' not in s:
    if s.count(anchor) != 1:
        raise SystemExit('Agent import anchor missing; no files changed')
if replacement not in s and s.count(needle) != 1:
    raise SystemExit('Agent dispatch anchor missing; no files changed')

h = holdout.read_text(encoding='utf-8')
tag='    tag = "holdout_smoke" if args.limit > 0 else "holdout"'
addon='    if os.getenv("P07_RETRIEVER") == "ranked":\n        tag += "_ranked"'
if addon not in h and h.count(tag) != 1:
    raise SystemExit('Holdout output tag anchor missing; no files changed')

shutil.copy2(agent, agent.with_name('agent_mvp.py.before_ranked'))
shutil.copy2(holdout, holdout.with_name('p07_holdout_benchmark.py.before_ranked'))
s = s.replace(anchor, 'from ranked_retrieval import ranked_search_docs\n\n' + anchor, 1) if 'from ranked_retrieval import ranked_search_docs' not in s else s
s = s.replace(needle, replacement, 1) if replacement not in s else s
h = h.replace(tag, tag + '\n' + addon, 1) if addon not in h else h
agent.write_text(s, encoding='utf-8')
holdout.write_text(h, encoding='utf-8')
print('Patched. Old P07 search untouched; use P07_RETRIEVER=ranked to select new backend.')
