"""Safely install a small date matcher into an existing P07 agent_mvp.py.

Run once from P07 repository root: python3 install_date_verifier.py
Never writes API keys or changes old evaluation traces.
"""
from pathlib import Path
import shutil

root = Path.cwd()
source = root / 'src' / 'agent_mvp.py'
date_module = root / 'src' / 'p07_date_facts.py'

if not source.is_file() or not date_module.is_file():
    raise SystemExit('Expected src/agent_mvp.py and src/p07_date_facts.py; run from P07 root')

code = source.read_text(encoding='utf-8')
anchor = 'def has_answer_fact(answer: str, keyword: str) -> bool:\n'
marker = '    from p07_date_facts import match_date_fact\n'
insertion = (
    '    from p07_date_facts import match_date_fact\n'
    '    date_match = match_date_fact(answer, keyword)\n'
    '    if date_match is not None:\n'
    '        return date_match\n'
)

if marker in code:
    print('Date verifier hook already installed. Nothing changed.')
elif code.count(anchor) != 1:
    raise SystemExit('Unable to find unique has_answer_fact() signature; nothing changed')
else:
    updated = code.replace(anchor, anchor + insertion, 1)
    compile(updated, str(source), 'exec')
    backup = source.with_name('agent_mvp.py.before_english_date_patch')
    if not backup.exists():
        shutil.copy2(source, backup)
    source.write_text(updated, encoding='utf-8')
    print('Installed date verifier. Backup:', backup)
