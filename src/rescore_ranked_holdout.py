"""Offline re-verification of saved P07 ranked-retrieval holdout traces.

No LLM/API calls. Original JSONLs are never overwritten.
From P07 root: python3 src/rescore_ranked_holdout.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from agent_mvp import FACT_ALIASES, aggregate, verify
from p07_holdout_benchmark import TASKS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "agent_mvp"
PREFIX = "holdout_ranked"


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}; run ranked holdout first")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def save_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def offline_rescore(records: list[dict], tasks: dict[str, dict], variant: str):
    output = []
    changes = []
    for record in records:
        task_id = record["task_id"]
        if task_id not in tasks:
            raise ValueError(f"Unknown task: {task_id}")
        previous = bool(record["passed"])
        verified, reasons = verify(tasks[task_id], record["events"], record["final"])
        # Running the verifier must NOT erase recorded runtime failures.
        runtime_reasons = [
            r for r in record.get("failure_reasons", [])
            if str(r).startswith("runtime_failure:")
        ]
        revised = dict(record)
        revised["passed"] = bool(verified) and not runtime_reasons
        revised["failure_reasons"] = reasons + runtime_reasons
        revised["verification_version"] = "offline_dates_v2"
        output.append(revised)
        changes.append({
            "task_id": task_id,
            "variant": variant,
            "old_passed": previous,
            "new_passed": revised["passed"],
            "old_reasons": record.get("failure_reasons", []),
            "new_reasons": revised["failure_reasons"],
            "changed": previous != revised["passed"] or record.get("failure_reasons", []) != revised["failure_reasons"],
        })
    return output, changes


def main() -> None:
    # Holdout originally configures these lexical aliases when running main().
    FACT_ALIASES.setdefault("monthly", ("monthly", "每月", "月度"))
    tasks = {task["id"]: task for task in TASKS}
    assert len(tasks) == len(TASKS), "Duplicate task IDs in the benchmark"

    all_changes = []
    by_variant = {}
    original_scores = {}
    for variant in ("baseline", "enhanced"):
        source_path = OUT / f"{PREFIX}_{variant}.jsonl"
        records = load_jsonl(source_path)
        actual_ids = [r["task_id"] for r in records]
        if len(actual_ids) != len(set(actual_ids)):
            raise ValueError(f"Duplicate rows in {source_path}")
        if set(actual_ids) != set(tasks):
            raise ValueError(f"Task IDs in {source_path} do not match holdout TASKS")
        original_scores[variant] = sum(bool(r["passed"]) for r in records)
        rescored, changes = offline_rescore(records, tasks, variant)
        save_jsonl(OUT / f"{PREFIX}_{variant}_rescored.jsonl", rescored)
        by_variant[variant] = rescored
        all_changes.extend(changes)

    baseline = by_variant["baseline"]
    enhanced = by_variant["enhanced"]
    bmap = {r["task_id"]: r for r in baseline}
    emap = {r["task_id"]: r for r in enhanced}
    improved = sorted(t for t in tasks if not bmap[t]["passed"] and emap[t]["passed"])
    regressed = sorted(t for t in tasks if bmap[t]["passed"] and not emap[t]["passed"])
    comparison = {
        "model": baseline[0].get("model"),
        "test_type": "offline re-verification of previously executed ranked holdout traces",
        "n_tasks": len(tasks),
        "original_reported_success": original_scores,
        "rescored_success": {
            "baseline": sum(r["passed"] for r in baseline),
            "enhanced": sum(r["passed"] for r in enhanced),
        },
        "baseline_metrics": aggregate(baseline, "offline_rescore", "baseline", PREFIX),
        "enhanced_metrics": aggregate(enhanced, "offline_rescore", "enhanced", PREFIX),
        "improved_task_ids": improved,
        "regressed_task_ids": regressed,
        "changed_verdicts": [r for r in all_changes if r["changed"]],
        "notes": [
            "No new model inference or tool execution: seconds and tool counts come from recorded traces.",
            "Same 16 hand-authored tasks were previously used to diagnose ranking errors; these are development/regression results, not a fresh independent benchmark.",
            "The deterministic verifier still performs lexical checks and is not a general semantic entailment or safety judge.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    out_json = OUT / "holdout_ranked_comparison_rescored.json"
    out_json.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with (OUT / "holdout_ranked_verifier_audit.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["task_id", "variant", "old_passed", "new_passed", "changed", "old_reasons", "new_reasons"])
        writer.writeheader()
        for entry in all_changes:
            row = dict(entry)
            for name in ("old_reasons", "new_reasons"):
                row[name] = json.dumps(row[name], ensure_ascii=False)
            writer.writerow(row)

    b_old = original_scores["baseline"]
    e_old = original_scores["enhanced"]
    b_new = comparison["rescored_success"]["baseline"]
    e_new = comparison["rescored_success"]["enhanced"]
    n = len(tasks)
    fail_b = sorted(t for t in tasks if not bmap[t]["passed"])
    fail_e = sorted(t for t in tasks if not emap[t]["passed"])
    delta = 100.0 * (e_new - b_new) / n
    report = f"""# 项目二：Agent Tool-Use 数据工厂 — Ranked Retrieval 离线评测复核

## 评测边界

- 模型：`{comparison['model']}`；基于既有真实模型输出的离线评分，**没有重新调用模型**。
- 数据：16 个手工构造的合成任务，新增模拟知识库与客户记录。
- 由于这 16 个任务已被用于发现和修复检索缺陷，**现在属于开发 / 回归测试，不能声称独立泛化提升**。

## 结果

| 同一 Ranked Retrieval 搜索器 | Baseline | Enhanced |
|---|---:|---:|
| 原始自动判定 | {b_old}/{n} ({b_old/n:.2%}) | {e_old}/{n} ({e_old/n:.2%}) |
| 更正日期语义后的离线判定 | {b_new}/{n} ({b_new/n:.2%}) | {e_new}/{n} ({e_new/n:.2%}) |
| 工具执行成功率 | {comparison['baseline_metrics']['tool_execution_success_rate']:.2%} | {comparison['enhanced_metrics']['tool_execution_success_rate']:.2%} |
| 工具调用次数 | {comparison['baseline_metrics']['tool_calls']} | {comparison['enhanced_metrics']['tool_calls']} |
| 平均任务耗时（原运行日志） | {comparison['baseline_metrics']['mean_seconds']}s | {comparison['enhanced_metrics']['mean_seconds']}s |

两种 Prompt 对照：Enhanced 比 Baseline 高 **{delta:g} 个百分点**（任务完成率；仅当前小样本回归集）。

## 误判审计

"""
    for ch in comparison["changed_verdicts"]:
        report += (
            f"- `{ch['variant']}/{ch['task_id']}`：{ch['old_passed']} → {ch['new_passed']}；"
            f"原失败原因 `{ch['old_reasons']}`；新失败原因 `{ch['new_reasons']}`。\n"
        )
    if not comparison["changed_verdicts"]:
        report += "- 没有检测到前后判定变化。\n"
    report += f"""
## 失败分析

- Baseline 未通过：{', '.join(f'`{t}`' for t in fail_b) if fail_b else '无'}。
- Enhanced 未通过：{', '.join(f'`{t}`' for t in fail_e) if fail_e else '无'}。
- Enhanced 相对 Baseline 改善的任务：{', '.join(f'`{t}`' for t in improved) if improved else '无'}。
- Enhanced 相对 Baseline 退步的任务：{', '.join(f'`{t}`' for t in regressed) if regressed else '无'}。

## 可复现性与限制

1. `python3 install_date_verifier.py` 安装日期比较钩子（不覆盖已有工具或提示词）。
2. `python3 -m unittest discover -s src -p 'test_p07_date_facts.py' -v` 验证多种日期写法、无效日期。
3. `python3 src/rescore_ranked_holdout.py` 对保存的 JSONL 执行离线重新评分；**不会覆盖原始 JSONL**。
4. 质量结论受限于预设 Task Verifier：文本包含匹配不等于语义正确，不具备反事实、否定句或权限系统完整审计能力。
5. 样本量很小，模型执行具有随机性，且曾根据这组任务修复检索排序；不能声称大规模泛化，也没有模型微调带来的收益。

## 数据工程贡献（基于当前可确认事实）

- 扩展原版 P07，从模板轨迹引入真实 `qwen-plus` 工具调用及多轮日志。
- 实现失败 Tool Call 正向监督过滤、Task 级 Train/Val 隔离、Evidence Verifier 与日期归一化。
- 增加轻量 Lexical Ranked Retrieval，研究 Top-1 检索召回和 Agent 最终任务完成间的关系。
- 建立 JSONL 轨迹记录、Verifier 复核、错误审计与 SFT 对话导出通路；本轮重新评分不产生新的 SFT 样本。
"""
    out_md = OUT / "holdout_ranked_report_rescored.md"
    out_md.write_text(report, encoding="utf-8")
    print(json.dumps({"before": original_scores, "after": comparison["rescored_success"], "changed": comparison["changed_verdicts"], "json": str(out_json), "report": str(out_md)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
