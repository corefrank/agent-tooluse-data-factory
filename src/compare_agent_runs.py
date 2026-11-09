"""Compare A/B agent prompts on the SAME small evaluation tasks.

Usage: python src/compare_agent_runs.py
Outputs: data/agent_mvp/comparison.json
These figures measure prompt/guardrail differences, NOT training improvements.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'agent_mvp'


def load(name):
    path = OUT / f'eval_{name}.jsonl'
    if not path.exists():
        raise SystemExit(f'Missing {path}; run: python src/agent_mvp.py --split eval --variant both')
    return {r['task_id']: r for line in path.read_text(encoding='utf-8').splitlines()
            if line.strip() for r in [json.loads(line)]}


def main():
    baseline, enhanced = load('baseline'), load('enhanced')
    if baseline.keys() != enhanced.keys():
        raise SystemExit('Mismatched task IDs: compare only identical evaluation sets.')
    ids = sorted(baseline)
    n = len(ids)
    if n == 0:
        raise SystemExit('Empty evaluation set.')
    b = sum(bool(baseline[x]['passed']) for x in ids)
    e = sum(bool(enhanced[x]['passed']) for x in ids)
    improved = [x for x in ids if not baseline[x]['passed'] and enhanced[x]['passed']]
    regressed = [x for x in ids if baseline[x]['passed'] and not enhanced[x]['passed']]
    result = {
        'comparison': 'same model, baseline prompt vs enhanced prompt with tool guidance',
        'n_tasks': n,
        'baseline_success': b,
        'enhanced_success': e,
        'baseline_success_rate': round(b / n, 4),
        'enhanced_success_rate': round(e / n, 4),
        'delta_percentage_points': round(100 * (e-b) / n, 2),
        'improved_task_ids': improved,
        'regressed_task_ids': regressed,
        'note': 'Small synthetic benchmark. Prompt intervention only; no claim of model finetuning or broad generalization.'
    }
    output_path = OUT / 'comparison.json'
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f'Saved to {output_path}')


if __name__ == '__main__':
    main()
