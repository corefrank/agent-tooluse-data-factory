from __future__ import annotations

from collections import Counter

from pipeline_utils import PROCESSED_DIR, REPORTS_DIR, TRAINING_DIR, ensure_standard_dirs, load_json, load_jsonl, write_json

TOOL_SCHEMA_FILE = PROCESSED_DIR / "tool_schemas.json"
TEMPLATE_FILE = PROCESSED_DIR / "trajectory_templates.json"
EXECUTED_FILE = PROCESSED_DIR / "executed_trajectories.jsonl"
SUMMARY_FILE = PROCESSED_DIR / "execution_summary.json"
MANIFEST_FILE = TRAINING_DIR / "training_manifest.json"
METRICS_FILE = REPORTS_DIR / "p7_metrics.json"
REPORT_FILE = REPORTS_DIR / "p7_report.md"


def main() -> None:
    ensure_standard_dirs()
    tool_schemas = load_json(TOOL_SCHEMA_FILE)
    templates = load_json(TEMPLATE_FILE)
    trajectories = load_jsonl(EXECUTED_FILE)
    execution_summary = load_json(SUMMARY_FILE)
    manifest = load_json(MANIFEST_FILE)

    successful_trajectories = [item for item in trajectories if item["final_success"]]
    recovery_cases = [item for item in trajectories if item["variant"] == "recovery"]
    safety_cases = [item for item in trajectories if item["variant"] == "block"]
    memory_cases = [item for item in trajectories if item["requires_memory"]]

    metrics = {
        "tool_schema_count": len(tool_schemas),
        "template_count": len(templates),
        "trajectory_count": len(trajectories),
        "category_distribution": dict(Counter(item["category"] for item in trajectories)),
        "variant_distribution": dict(Counter(item["variant"] for item in trajectories)),
        "tool_call_success_rate": execution_summary["tool_call_success_rate"],
        "trajectory_success_rate": execution_summary["trajectory_success_rate"],
        "recovery_success_rate": round(
            sum(item["final_success"] for item in recovery_cases) / max(1, len(recovery_cases)),
            4,
        ),
        "unsafe_block_rate": round(
            sum(item["final_success"] for item in safety_cases) / max(1, len(safety_cases)),
            4,
        ),
        "unauthorized_tool_call_rate": round(
            sum(item["unauthorized_tool_call"] for item in safety_cases) / max(1, len(safety_cases)),
            4,
        ),
        "memory_success_rate": round(
            sum(item["memory_success"] for item in memory_cases) / max(1, len(memory_cases)),
            4,
        ),
        "avg_tool_calls_per_success": round(
            sum(item["tool_call_count"] for item in successful_trajectories) / max(1, len(successful_trajectories)),
            4,
        ),
        "training_manifest": manifest,
        "estimated_manual_review_hours": round(len(trajectories) * 2 / 60, 2),
        "estimated_manual_review_cost_rmb": round(len(trajectories) * 2 * 100 / 60, 2),
    }
    write_json(metrics, METRICS_FILE)

    report = f"""# P7 Agent Tool-Use Data Factory Report

## 1. 场景定义与工具边界

- 工具 schema 数量：{metrics['tool_schema_count']}
- 轨迹模板数量：{metrics['template_count']}
- 任务轨迹总数：{metrics['trajectory_count']}
- 类别分布：{metrics['category_distribution']}

## 2. Tool Schema 与轨迹模板

- 已覆盖搜索、数据库、日历、代码执行、memory read/write 等工具。
- 已覆盖单步调用、多步链路、参数修复、多轮记忆与安全拒绝模板。
- 轨迹类型分布：{metrics['variant_distribution']}

## 3. 成功轨迹与失败恢复

- 工具调用成功率：{metrics['tool_call_success_rate']}
- 整体轨迹成功率：{metrics['trajectory_success_rate']}
- 恢复轨迹成功率：{metrics['recovery_success_rate']}

## 4. 多轮状态与记忆接入

- 记忆相关轨迹成功率：{metrics['memory_success_rate']}
- 成功轨迹平均工具调用步数：{metrics['avg_tool_calls_per_success']}

## 5. 评测与安全治理

- 安全拒绝成功率：{metrics['unsafe_block_rate']}
- 未授权工具调用率：{metrics['unauthorized_tool_call_rate']}
- 训练样本数：{manifest['num_records']}
- train/val/smoke：{manifest['num_train_records']}/{manifest['num_val_records']}/{manifest['num_smoke_records']}

## 6. 扩展方向

- 从工具调用扩展到复杂 Agent workflow 与跨会话记忆。
- 引入更真实的权限系统、恶意参数库和环境不确定性模拟。
- 把恢复轨迹与在线反馈闭环结合，支持更难的多步恢复任务。
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print("✅ P7 报告生成完成。")
    print(report)


if __name__ == "__main__":
    main()
