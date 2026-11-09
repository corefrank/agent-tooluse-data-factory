from __future__ import annotations

import subprocess
from pathlib import Path

from pipeline_utils import PROCESSED_DIR, REPORTS_DIR, TRAINING_DIR, ensure_standard_dirs, load_json, load_jsonl, write_json

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
TOOL_SCHEMA_FILE = PROCESSED_DIR / "tool_schemas.json"
TEMPLATE_FILE = PROCESSED_DIR / "trajectory_templates.json"
EXECUTED_FILE = PROCESSED_DIR / "executed_trajectories.jsonl"
TOOL_LOG_FILE = PROCESSED_DIR / "tool_execution_log.jsonl"
MANIFEST_FILE = TRAINING_DIR / "training_manifest.json"
TRAIN_FILE = TRAINING_DIR / "train.jsonl"
VAL_FILE = TRAINING_DIR / "val.jsonl"
SMOKE_FILE = TRAINING_DIR / "smoke_test.jsonl"
RESULTS_FILE = REPORTS_DIR / "p7_test_results.json"
REPORT_FILE = REPORTS_DIR / "p7_test_report.md"


def run_command(command: list[str], name: str) -> dict:
    result = subprocess.run(command, capture_output=True, text=True)
    return {
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "passed": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def main() -> None:
    ensure_standard_dirs()
    tool_schemas = load_json(TOOL_SCHEMA_FILE)
    templates = load_json(TEMPLATE_FILE)
    executed = load_jsonl(EXECUTED_FILE)
    tool_logs = load_jsonl(TOOL_LOG_FILE)
    manifest = load_json(MANIFEST_FILE)
    train_records = load_jsonl(TRAIN_FILE)
    val_records = load_jsonl(VAL_FILE)
    smoke_records = load_jsonl(SMOKE_FILE)

    py_files = sorted(str(path) for path in SRC_DIR.glob("*.py"))
    command_checks = [
        run_command(["python", "-m", "py_compile", *py_files], "py_compile"),
        run_command(["python", str(SRC_DIR / "evaluate_tooluse.py")], "evaluate_tooluse"),
    ]

    dataset_checks = []
    dataset_checks.append(
        {
            "name": "required_files_exist",
            "passed": all(path.exists() for path in [TOOL_SCHEMA_FILE, TEMPLATE_FILE, EXECUTED_FILE, TOOL_LOG_FILE, MANIFEST_FILE]),
            "details": {},
        }
    )
    dataset_checks.append(
        {
            "name": "tool_schema_fields_complete",
            "passed": all(
                {"name", "description", "parameters", "returns", "errors", "safety_boundary"}.issubset(schema)
                for schema in tool_schemas
            ),
            "details": {"tool_schema_count": len(tool_schemas)},
        }
    )
    dataset_checks.append(
        {
            "name": "templates_cover_single_multi_and_safety",
            "passed": {"single_tool_success", "multi_tool_chain", "multi_turn_memory", "safety_refusal"}.issubset(
                {item["template_id"] for item in templates}
            ),
            "details": {"template_ids": [item["template_id"] for item in templates]},
        }
    )
    dataset_checks.append(
        {
            "name": "variant_coverage",
            "passed": {"success", "recovery", "block"}.issubset({item["variant"] for item in executed}),
            "details": {"variant_distribution": load_json(PROCESSED_DIR / "execution_summary.json")["variant_distribution"]},
        }
    )
    dataset_checks.append(
        {
            "name": "observations_and_decision_chain_present",
            "passed": all(
                any(event["event_type"] == "assistant_plan" for event in item["events"])
                and any(event["event_type"] == "observation" for event in item["events"] if item["tool_call_count"] > 0)
                or item["variant"] == "block"
                for item in executed
            ),
            "details": {"num_trajectories": len(executed)},
        }
    )
    dataset_checks.append(
        {
            "name": "memory_cases_succeed",
            "passed": all(item["memory_success"] for item in executed if item["requires_memory"]),
            "details": {"memory_case_count": sum(item["requires_memory"] for item in executed)},
        }
    )
    dataset_checks.append(
        {
            "name": "safety_cases_blocked_without_tools",
            "passed": all(item["final_success"] and item["tool_call_count"] == 0 for item in executed if item["variant"] == "block"),
            "details": {"safety_case_count": sum(item["variant"] == "block" for item in executed)},
        }
    )
    train_ids = {item["record_id"] for item in train_records}
    val_ids = {item["record_id"] for item in val_records}
    dataset_checks.append(
        {
            "name": "train_val_no_overlap",
            "passed": len(train_ids & val_ids) == 0,
            "details": {"overlap": len(train_ids & val_ids)},
        }
    )
    smoke_types = {
        "general": any(not item["requires_memory"] and not item["is_safety_case"] for item in smoke_records),
        "memory": any(item["requires_memory"] for item in smoke_records),
        "safety": any(item["is_safety_case"] for item in smoke_records),
    }
    dataset_checks.append(
        {
            "name": "smoke_covers_general_memory_safety",
            "passed": all(smoke_types.values()),
            "details": smoke_types,
        }
    )
    dataset_checks.append(
        {
            "name": "manifest_matches_record_count",
            "passed": manifest["num_records"] == len(train_records) + len(val_records),
            "details": manifest,
        }
    )

    overall_passed = all(item["passed"] for item in command_checks + dataset_checks)
    results = {
        "overall_passed": overall_passed,
        "total_checks": len(command_checks) + len(dataset_checks),
        "passed_checks": sum(item["passed"] for item in command_checks + dataset_checks),
        "command_checks": command_checks,
        "dataset_checks": dataset_checks,
    }
    write_json(results, RESULTS_FILE)

    lines = [
        "# P7 Test Report",
        "",
        f"- Overall status: {'PASS' if overall_passed else 'FAIL'}",
        f"- Passed checks: {results['passed_checks']}/{results['total_checks']}",
        "",
        "## Command Checks",
        "",
    ]
    for item in command_checks:
        lines.append(f"- {item['name']}: {'PASS' if item['passed'] else 'FAIL'}")
        lines.append(f"  - Command: `{' '.join(item['command'])}`")
    lines.extend(["", "## Dataset Checks", ""])
    for item in dataset_checks:
        lines.append(f"- {item['name']}: {'PASS' if item['passed'] else 'FAIL'}")
        lines.append(f"  - Details: `{item['details']}`")

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print("✅ P7 测试完成。")
    print(results)


if __name__ == "__main__":
    main()
