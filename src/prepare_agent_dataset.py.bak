from __future__ import annotations

from collections import Counter, defaultdict

from pipeline_utils import PROCESSED_DIR, TRAINING_DIR, deterministic_bucket, ensure_standard_dirs, estimated_tokens, load_jsonl, write_json, write_jsonl

EXECUTED_FILE = PROCESSED_DIR / "executed_trajectories.jsonl"
FINAL_FILE = TRAINING_DIR / "agent_tooluse_dataset.jsonl"
TRAIN_FILE = TRAINING_DIR / "train.jsonl"
VAL_FILE = TRAINING_DIR / "val.jsonl"
SMOKE_FILE = TRAINING_DIR / "smoke_test.jsonl"
MANIFEST_FILE = TRAINING_DIR / "training_manifest.json"


def render_context(events: list[dict]) -> list[str]:
    rendered = []
    for event in events:
        if event["event_type"] in {"user", "assistant_plan", "assistant_final"}:
            rendered.append(f"{event['event_type']}: {event['content']}")
        elif event["event_type"] == "tool_call":
            rendered.append(f"tool_call: {event['tool_name']} {event['arguments']}")
        else:
            rendered.append(f"observation: {event['tool_name']} -> {event['content']}")
    return rendered


def build_records(trajectory: dict) -> list[dict]:
    records: list[dict] = []
    history: list[dict] = []
    step_idx = 0
    for event in trajectory["events"]:
        if event["event_type"] in {"assistant_plan", "tool_call", "assistant_final"}:
            step_idx += 1
            record = {
                "record_id": f"{trajectory['trajectory_id']}_step_{step_idx}",
                "trajectory_id": trajectory["trajectory_id"],
                "task_id": trajectory["task_id"],
                "category": trajectory["category"],
                "variant": trajectory["variant"],
                "turn_type": trajectory["turn_type"],
                "requires_memory": trajectory["requires_memory"],
                "is_safety_case": trajectory["is_safety_case"],
                "context": render_context(history),
                "target_event_type": event["event_type"],
                "target": event,
                "trajectory_final_success": trajectory["final_success"],
            }
            records.append(record)
        history.append(event)
    return records


def main() -> None:
    ensure_standard_dirs()
    trajectories = load_jsonl(EXECUTED_FILE)
    records: list[dict] = []
    for trajectory in trajectories:
        records.extend(build_records(trajectory))

    records = sorted(records, key=lambda item: item["record_id"])
    train_records: list[dict] = []
    val_records: list[dict] = []
    smoke_groups: dict[str, list[dict]] = defaultdict(list)

    for record in records:
        if deterministic_bucket(record["trajectory_id"]) < 85:
            train_records.append(record)
        else:
            val_records.append(record)

        smoke_key = "memory" if record["requires_memory"] else "safety" if record["is_safety_case"] else "general"
        if len(smoke_groups[smoke_key]) < 4:
            smoke_groups[smoke_key].append(record)

    smoke_records: list[dict] = []
    for key in ["general", "memory", "safety"]:
        smoke_records.extend(smoke_groups[key])

    manifest = {
        "num_records": len(records),
        "num_train_records": len(train_records),
        "num_val_records": len(val_records),
        "num_smoke_records": len(smoke_records),
        "category_distribution": dict(Counter(record["category"] for record in records)),
        "variant_distribution": dict(Counter(record["variant"] for record in records)),
        "target_event_distribution": dict(Counter(record["target_event_type"] for record in records)),
        "safety_record_count": sum(record["is_safety_case"] for record in records),
        "memory_record_count": sum(record["requires_memory"] for record in records),
        "estimated_tokens_total": sum(
            estimated_tokens(" ".join(record["context"])) + estimated_tokens(str(record["target"]))
            for record in records
        ),
    }

    write_jsonl(records, FINAL_FILE)
    write_jsonl(train_records, TRAIN_FILE)
    write_jsonl(val_records, VAL_FILE)
    write_jsonl(smoke_records, SMOKE_FILE)
    write_json(manifest, MANIFEST_FILE)
    print("✅ P7 训练数据组织完成。")
    print(manifest)


if __name__ == "__main__":
    main()
